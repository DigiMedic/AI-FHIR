// frontend/src/components/PatientCard.js
import React from 'react';
import { formatFhirDateTime, formatGender } from '../utils/formatters';
import { findRodneCislo } from '../utils/fhirUtils';

const PatientCard = ({ resource }) => {
  if (!resource || resource.resourceType !== "Patient") {
    return <p>Neplatná data pro komponentu PatientCard.</p>;
  }

  const patientName = resource.name?.[0]?.text ||
                      `${resource.name?.[0]?.given?.join(' ') || ''} ${resource.name?.[0]?.family || ''}`.trim() ||
                      'N/A';

  return (
    <div className="patient-data">
      <h4>Pacient (ID: {resource.id || 'N/A'})</h4>
      <p><strong>Jméno:</strong> {patientName}</p>
      <p><strong>Datum narození:</strong> {formatFhirDateTime(resource.birthDate)}</p>
      <p><strong>Pohlaví:</strong> {formatGender(resource.gender)}</p>
      <p><strong>Rodné číslo:</strong> {findRodneCislo(resource.identifier)}</p>
    </div>
  );
};

export default PatientCard;
