// frontend/src/components/QualityIssueItem.js
import React from 'react';
import CorrectionForm from './CorrectionForm'; // Bude potřeba pro zobrazení formuláře

const QualityIssueItem = ({
  issue,
  index,
  onStartCorrection,
  isEditingThisIssue,
  isAnyIssueEditing,
  isLoading,
  // Props pro CorrectionForm, pokud je zobrazen
  correctionSuggestion,
  correctionComment, // Nová prop
  onSuggestionChange,
  onCorrectionCommentChange, // Nová prop
  onSubmitCorrection,
  onCancelCorrection
}) => {
  if (!issue) return null;

  return (
    <div className={`quality-issue quality-issue-${issue.level?.toLowerCase() || 'info'}`}>
      <p><strong>Úroveň:</strong> {issue.level || 'N/A'}</p>
      <p><strong>Zpráva:</strong> {issue.message || 'N/A'}</p>
      {(issue.field || issue.path) && <p><strong>Pole/Cesta:</strong> {issue.field || issue.path}</p>}
      {issue.value !== undefined && <p><strong>Hodnota:</strong> {String(issue.value)}</p>}

      {isEditingThisIssue ? (
        <CorrectionForm
          issue={issue}
          suggestion={correctionSuggestion}
          comment={correctionComment} // Předání nové prop
          onSuggestionChange={onSuggestionChange}
          onCommentChange={onCorrectionCommentChange} // Předání nové prop
          onSubmit={() => onSubmitCorrection(index)} // Předáme index pro submit handler v App.js
          onCancel={onCancelCorrection}
          isLoading={isLoading}
        />
      ) : (
        <button
          onClick={() => onStartCorrection(index)}
          disabled={isLoading || isAnyIssueEditing}
          style={{ marginTop: '10px', padding: '5px 10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          data-testid={`suggest-correction-btn-${index}`}
        >
          Navrhnout korekci
        </button>
      )}
    </div>
  );
};

export default QualityIssueItem;
