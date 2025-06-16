// frontend/src/components/QualityIssueItem.js
import React from 'react';
import CorrectionForm from './CorrectionForm'; // Bude potřeba pro zobrazení formuláře
// Předpokládáme, že App.css je importován globálně v App.js nebo index.js
// Pokud ne, odkomentujte: import './QualityIssueItem.css'; nebo '../App.css';

const QualityIssueItem = ({
  issue,
  index,
  onStartCorrection,
  isEditingThisIssue,
  isAnyIssueEditing,
  isLoading,
  // Props pro CorrectionForm, pokud je zobrazen
  correctionSuggestion,
  correctionComment,
  onSuggestionChange,
  onCorrectionCommentChange,
  onSubmitCorrection,
  onCancelCorrection
}) => {
  if (!issue) return null;

  const getIssueLevelModifierClass = (level) => {
    if (!level) return 'quality-issue-item--info'; // Default
    switch (level.toLowerCase()) {
      case 'critical': // Přidáno 'critical' pro mapování na error
      case 'error':
        return 'quality-issue-item--error';
      case 'warning':
        return 'quality-issue-item--warning';
      case 'info':
      default:
        return 'quality-issue-item--info';
    }
  };

  const fieldDisplay = issue.field || issue.path || 'N/A';
  const valueDisplay = issue.value !== undefined && issue.value !== null ? String(issue.value) : 'N/A';
  const messageDisplay = issue.message || 'Neznámý problém';
  const levelDisplay = issue.level || 'Info';

  return (
    <div className={`quality-issue-item ${getIssueLevelModifierClass(issue.level)}`}>
      <p><strong>Problém:</strong> {messageDisplay}</p>
      <p><strong>Pole:</strong> {fieldDisplay}</p>
      <p><strong>Původní hodnota:</strong> {valueDisplay}</p>
      <p><strong>Úroveň:</strong> {levelDisplay}</p>

      {isEditingThisIssue ? (
        <CorrectionForm
          issue={issue} // issue se předává pro kontext, pokud ho CorrectionForm potřebuje
          suggestion={correctionSuggestion}
          comment={correctionComment}
          onSuggestionChange={onSuggestionChange}
          onCommentChange={onCorrectionCommentChange}
          onSubmit={() => onSubmitCorrection(index)}
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
