// frontend/src/components/QualityIssuesSection.js
import React from 'react';
import QualityIssueItem from './QualityIssueItem';

const QualityIssuesSection = ({
  issues,
  correctionStatus,
  editingIssueIndex,
  correctionSuggestion,
  isLoading,
  onStartCorrection,
  onCancelCorrection,
  onSuggestionChange,
  onSubmitCorrection,
  // selectedFile // selectedFile není přímo potřeba zde, ale v App.js pro handleSubmitCorrection
}) => {
  if (issues === undefined) { // Pokud issues ještě nejsou definované (např. před prvním uploadem)
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
            onStartCorrection={onStartCorrection}
            isEditingThisIssue={editingIssueIndex === index}
            isAnyIssueEditing={editingIssueIndex !== null && editingIssueIndex !== index}
            isLoading={isLoading}
            correctionSuggestion={editingIssueIndex === index ? correctionSuggestion : ''}
            onSuggestionChange={onSuggestionChange}
            onSubmitCorrection={onSubmitCorrection} // Předáváme handleSubmitCorrection z App.js
            onCancelCorrection={onCancelCorrection}
          />
        ))
      ) : (
        <p>Nebyly nalezeny žádné problémy s kvalitou dat.</p>
      )}
    </section>
  );
};

export default QualityIssuesSection;
