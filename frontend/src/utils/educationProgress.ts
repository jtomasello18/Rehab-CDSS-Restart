import curriculum from '../data/education.json';

export const patients = curriculum.patients;
export const domains = curriculum.domains;
export const sources = curriculum.sources;
export type Patient = typeof patients[number];
export type Question = Patient['questions'][number];
export type Confidence = 'high' | 'review' | null;
export type Answer = { option: number; confidence: Confidence };
export type Progress = { version: 1; answers: Record<string, Record<string, Answer>> };
export const emptyProgress = (): Progress => ({ version: 1, answers: {} });
const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

// Only curriculum IDs and valid choices survive a restored session. Scores are derived.
export function normalizeProgress(value: unknown): Progress {
  const result = emptyProgress();
  if (!record(value) || value.version !== 1 || !record(value.answers)) return result;
  for (const patient of patients) {
    const entries = value.answers[patient.id];
    if (!record(entries)) continue;
    for (const question of patient.questions) {
      const answer = entries[question.id];
      if (!record(answer) || !Number.isInteger(answer.option)
          || Number(answer.option) < 0 || Number(answer.option) >= question.options.length) continue;
      result.answers[patient.id] ??= {};
      result.answers[patient.id][question.id] = {
        option: Number(answer.option),
        confidence: answer.confidence === 'high' || answer.confidence === 'review' ? answer.confidence : null,
      };
    }
  }
  return result;
}

export function submitAnswer(progress: Progress, patient: Patient, question: Question, answer: Answer): Progress {
  if (progress.answers[patient.id]?.[question.id]) return progress;
  return normalizeProgress({ version: 1, answers: { ...progress.answers,
    [patient.id]: { ...progress.answers[patient.id], [question.id]: answer },
  } });
}

export function resetPatient(progress: Progress, patientId: string): Progress {
  const answers = { ...progress.answers };
  delete answers[patientId];
  return { version: 1, answers };
}

export function patientStats(progress: Progress, patient: Patient) {
  const answered = patient.questions.filter(q => progress.answers[patient.id]?.[q.id]);
  const correct = answered.filter(q => progress.answers[patient.id][q.id].option === q.correct).length;
  const complete = answered.length === patient.questions.length;
  return { answered: answered.length, total: patient.questions.length, correct, complete,
    mastery: Math.round(100 * correct / patient.questions.length),
    completion: Math.round(100 * answered.length / patient.questions.length),
    // Demo learning points only: 0.05 per first answer; completion tops a module up to 0.25.
    hours: complete ? 0.25 : answered.length * 0.05,
  };
}

export function overallStats(progress: Progress) {
  const stats = patients.map(patient => patientStats(progress, patient));
  const answered = stats.reduce((sum, s) => sum + s.answered, 0);
  const correct = stats.reduce((sum, s) => sum + s.correct, 0);
  return { answered, correct, accuracy: answered ? Math.round(100 * correct / answered) : 0,
    hours: Math.round(stats.reduce((sum, s) => sum + s.hours, 0) * 100) / 100,
    completed: stats.filter(s => s.complete).length,
    domains: domains.map(domain => {
      const answers = patients.flatMap(patient => patient.questions.filter(q =>
        q.domain === domain.id && progress.answers[patient.id]?.[q.id]
      ).map(q => progress.answers[patient.id][q.id].option === q.correct));
      const correct = answers.filter(Boolean).length;
      return { ...domain, answered: answers.length, correct,
        accuracy: answers.length ? Math.round(100 * correct / answers.length) : 0 };
    }),
  };
}
