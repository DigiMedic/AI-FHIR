// frontend/src/components/ConditionCard.js
import React from 'react';
import { formatFhirDateTime } from '../utils/formatters';

const ConditionCard = ({ resource }) => {
  if (!resource || resource.resourceType !== "Condition") {
    return <p>Neplatná data pro komponentu ConditionCard.</p>;
  }

  return (
    <div className="condition-data">
      <h4>Diagnóza (ID: {resource.id || 'N/A'})</h4>
      <p><strong>Text diagnózy:</strong> {resource.code?.text || 'N/A'}</p>
      <p><strong>Datum záznamu:</strong> {formatFhirDateTime(resource.recordedDate)}</p>
      <p><strong>Klinický stav:</strong> {resource.clinicalStatus?.coding?.[0]?.display || resource.clinicalStatus?.coding?.[0]?.code || 'N/A'}</p>
      <p><strong>Stav ověření:</strong> {resource.verificationStatus?.coding?.[0]?.display || resource.verificationStatus?.coding?.[0]?.code || 'N/A'}</p>
    </div>
  );
};

export default ConditionCard;
