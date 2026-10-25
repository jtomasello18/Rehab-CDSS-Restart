import React from 'react'
import { useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { Streamlit, withStreamlitConnection } from 'streamlit-component-lib'
import ScribeTab from './components/ScribeTab'
import ProgressNoteTab from './components/ProgressNoteTab'
import PatientBiometricsTab from './components/PatientBiometricsTab'
import LiteratureEvidenceTab from './components/LiteratureEvidenceTab'
import EducationTab from './components/EducationTab'
import './index.css'

function App({ args = {} }) {
  const view = args.view

  useEffect(() => {
    const updateFrameHeight = () => Streamlit.setFrameHeight()
    updateFrameHeight()

    const resizeObserver = new ResizeObserver(updateFrameHeight)
    resizeObserver.observe(document.body)

    return () => resizeObserver.disconnect()
  }, [])

  switch (view) {
    case 'progress_note':
      return <ProgressNoteTab args={args} />
    case 'patient_biometrics':
      return <PatientBiometricsTab />
    case 'literature_evidence':
      return <LiteratureEvidenceTab />
    case 'scribe':
      return <ScribeTab args={args} />
    case 'education':
      return <EducationTab args={args} />
    default:
      return <ProgressNoteTab />
  }
}

const ConnectedApp = withStreamlitConnection(App)

createRoot(document.getElementById('root')).render(
  <React.StrictMode><ConnectedApp /></React.StrictMode>,
)
