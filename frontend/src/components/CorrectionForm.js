// frontend/src/components/CorrectionForm.js
import React from 'react';

const CorrectionForm = ({
  issue,
  suggestion,
  comment, // Nová prop
  onSuggestionChange,
  onCommentChange, // Nová prop
  onSubmit,
  onCancel,
  isLoading
}) => {
  if (!issue) return null;

  const fieldIdentifier = issue.field || issue.path || 'položku';

  return (
    <div className="correction-form" style={{ marginTop: '10px', marginBottom: '10px', padding: '10px', border: '1px dashed #999', backgroundColor: '#f9f9f9' }}>
      <div>
        <label htmlFor={`suggestion-${fieldIdentifier}`} style={{ display: 'block', marginBottom: '5px' }}>
          Navrhovaná korekce pro "{fieldIdentifier}":
        </label>
        <input
          id={`suggestion-${fieldIdentifier}`}
          type="text"
          value={suggestion}
          onChange={onSuggestionChange}
          style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '100%', boxSizing: 'border-box' }}
          disabled={isLoading}
        />
      </div>
      <div style={{marginTop: '10px'}}>
        <label htmlFor={`comment-${fieldIdentifier}`} style={{ display: 'block', marginBottom: '5px' }}>
          Komentář (volitelné):
        </label>
        <textarea
          id={`comment-${fieldIdentifier}`}
          value={comment}
          onChange={onCommentChange}
          rows={3}
          style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', width: '100%', boxSizing: 'border-box' }}
          disabled={isLoading}
        />
      </div>
      <div style={{marginTop: '15px', textAlign: 'right'}}>
        <button
          onClick={onSubmit}
          disabled={isLoading}
          style={{ marginRight: '10px', padding: '8px 15px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {isLoading ? 'Odesílání...' : 'Odeslat návrh'}
        </button>
        <button
          onClick={onCancel}
          disabled={isLoading}
          style={{ padding: '8px 15px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Zrušit
        </button>
      </div>
    </div>
  );
};

export default CorrectionForm;
