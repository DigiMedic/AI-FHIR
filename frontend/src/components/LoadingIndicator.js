// frontend/src/components/LoadingIndicator.js
import React from 'react';

const LoadingIndicator = () => {
  return (
    <p className="loading-message" style={{padding: '20px', textAlign: 'center'}}>
      Zpracovávám soubor, prosím čekejte...
    </p>
  );
};

export default LoadingIndicator;
