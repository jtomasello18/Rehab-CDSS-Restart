/** Normalize common clinical dictation errors before transcript review. */
export const applyClinicalCorrections = (text: string): string => {
  let corrected = text;
  corrected = corrected.replace(/\b(\d{2,3})\s+over\s+(\d{2,3})\b/gi, '$1/$2');
  corrected = corrected.replace(/\b(abnormal|antalgic|slow|steppage|trendelenburg|hemiparetic)\s+gay\b/gi, '$1 gait');
  corrected = corrected.replace(/\bgay\b/gi, 'gait');
  corrected = corrected.replace(/\bgate\b/gi, 'gait');
  corrected = corrected.replace(/\bcyrriax\b/gi, 'Cyriax');
  return corrected;
};
