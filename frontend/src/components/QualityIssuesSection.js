// frontend/src/components/QualityIssuesSection.js
import React, { useState } from 'react'; // Přidat useState
import QualityIssueItem from './QualityIssueItem';

const QualityIssuesSection = ({
  issues,
  // ODEBRÁNY propy z App.js: correctionStatus, editingIssueIndex, correctionSuggestion, correctionComment,
  // onStartCorrection, onCancelCorrection, onSuggestionChange, onCorrectionCommentChange, onSubmitCorrection
  // PŘIDÁNY PROPY Z APP.JS:
  selectedFile,
  API_URL,
  isLoading,
  setIsLoading
}) => {
  // PŘIDÁNY NOVÉ STAVY:
  const [editingIssueIndex, setEditingIssueIndex] = useState(null);
  const [correctionSuggestion, setCorrectionSuggestion] = useState('');
  const [correctionComment, setCorrectionComment] = useState('');
  const [correctionStatus, setCorrectionStatus] = useState('');


  // PŘIDÁNY PŘESUNUTÉ HANDLERY Z APP.JS
  const handleStartCorrection = (index) => {
    setEditingIssueIndex(index);
    const issueValue = issues[index]?.value;
    setCorrectionSuggestion(issueValue !== undefined && issueValue !== null ? String(issueValue) : '');
    setCorrectionComment(''); // Reset komentáře při otevření nového formuláře
    setCorrectionStatus('');
  };

  const handleCancelCorrection = () => {
    setEditingIssueIndex(null);
    setCorrectionSuggestion('');
    setCorrectionComment('');
  };

  const handleSuggestionChange = (event) => {
    setCorrectionSuggestion(event.target.value);
  };

  const handleCorrectionCommentChange = (event) => {
    setCorrectionComment(event.target.value);
  };

  const handleSubmitCorrection = async (index) => {
    const originalIssue = issues[index];
    if (!originalIssue) {
      setCorrectionStatus("Chyba: Původní problém s kvalitou nenalezen.");
      return;
    }

    const payload = {
      originalIssue: {
        level: originalIssue.level,
        message: originalIssue.message,
        field: originalIssue.field || originalIssue.path,
        value: originalIssue.value !== undefined ? String(originalIssue.value) : null
      },
      suggestedValue: correctionSuggestion,
      fileName: selectedFile ? selectedFile.name : 'N/A',
      comment: correctionComment
    };

    setIsLoading(true); // Použití setIsLoading z propů
    setCorrectionStatus('');

    try {
      const response = await fetch(`${API_URL}/api/suggest_correction`, { // Použití API_URL z propů
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json();

      if (response.ok) {
        setCorrectionStatus(responseData.message || "Návrh úspěšně odeslán.");
      } else {
        let errorMsg = responseData.detail || `Chyba serveru: ${response.status}`;
        if (Array.isArray(responseData.detail) && responseData.detail.length > 0 && responseData.detail[0].msg) {
           errorMsg = `Chyba validace: ${responseData.detail[0].msg} (pro pole: ${responseData.detail[0].loc?.join('->') || 'N/A'})`;
        }
        setCorrectionStatus(errorMsg);
      }
    } catch (networkError) {
      console.error("Network error submitting correction:", networkError);
      setCorrectionStatus("Chyba sítě při odesílání návrhu.");
    } finally {
      setIsLoading(false); // Použití setIsLoading z propů
      setEditingIssueIndex(null);
      setCorrectionSuggestion('');
      setCorrectionComment('');
    }
  };

  if (issues === undefined) {
    return null;
  }

  return (
    <section className="quality-issues-section">
      <h3>Problémy s kvalitou dat</h3>
      {correctionStatus && (
        <p
          className="correction-status-message"
          style={{
            color: correctionStatus.startsWith('Chyba') ? 'red' : 'green',
            fontWeight: 'bold',
            marginBottom: '15px',
            padding: '10px',
            border: `1px solid ${correctionStatus.startsWith('Chyba') ? 'red' : 'green'}`
          }}
        >
          {correctionStatus}
        </p>
      )}
      {issues.length > 0 ? (
        issues.map((issue, index) => (
          <QualityIssueItem
            key={index}
            issue={issue}
            index={index}
            onStartCorrection={handleStartCorrection} // Nyní z QualityIssuesSection
            isEditingThisIssue={editingIssueIndex === index}
            isAnyIssueEditing={editingIssueIndex !== null && editingIssueIndex !== index}
            isLoading={isLoading} // Předáno z App.js
            correctionSuggestion={editingIssueIndex === index ? correctionSuggestion : ''}
            correctionComment={editingIssueIndex === index ? correctionComment : ''} // Přidáno pro QualityIssueItem
            onSuggestionChange={handleSuggestionChange} // Nyní z QualityIssuesSection
            onCorrectionCommentChange={handleCorrectionCommentChange} // Nyní z QualityIssuesSection
            onSubmitCorrection={handleSubmitCorrection} // Nyní z QualityIssuesSection
            onCancelCorrection={handleCancelCorrection} // Nyní z QualityIssuesSection
          />
        ))
      ) : (
        <p>Nebyly nalezeny žádné problémy s kvalitou dat.</p>
      )}
    </section>
  );
};

export default QualityIssuesSection;
