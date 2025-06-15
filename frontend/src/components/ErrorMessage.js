// frontend/src/components/ErrorMessage.js
import React from 'react';

const ErrorMessage = ({ message }) => {
  if (!message) {
    return null;
  }
  return (
    <p className="error-message" style={{color: 'red', padding: '10px', border: '1px solid red', backgroundColor: '#ffe0e0'}}>
      {message}
    </p>
  );
};

export default ErrorMessage;
