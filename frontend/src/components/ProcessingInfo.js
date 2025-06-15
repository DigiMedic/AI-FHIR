// frontend/src/components/ProcessingInfo.js
import React from 'react';

const ProcessingInfo = ({ processingStatusText }) => {
  if (!processingStatusText) {
    return null;
  }
  return (
    <section className="extracted-text-section">
      {/* Ponechal jsem původní název třídy, pokud na něm závisí styly */}
      <h3>Stav zpracování souboru:</h3>
      <pre>{processingStatusText}</pre>
    </section>
  );
};

export default ProcessingInfo;
