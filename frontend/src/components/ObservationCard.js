// frontend/src/components/ObservationCard.js
import React from 'react';
import { formatFhirDateTime } from '../utils/formatters';

const ObservationCard = ({ resource }) => {
  if (!resource || resource.resourceType !== "Observation") {
    return <p>Neplatná data pro komponentu ObservationCard.</p>;
  }

  const observationText = resource.code?.text || 'N/A';
  const observationId = resource.id || 'N/A';
  const effectiveDateTime = formatFhirDateTime(resource.effectiveDateTime);
  const value = resource.valueQuantity?.value || 'N/A';
  const unit = resource.valueQuantity?.unit || 'N/A';

  // Specifické zobrazení pro Krevní tlak
  if (observationText === "Krevní tlak") {
    const systolicComp = resource.component?.find(comp => comp.code?.coding?.[0]?.code === "8480-6");
    const diastolicComp = resource.component?.find(comp => comp.code?.coding?.[0]?.code === "8462-4");

    return (
      <div className="observation-data">
        <h4>Pozorování: Krevní tlak (ID: {observationId})</h4>
        <p><strong>Datum a čas měření:</strong> {effectiveDateTime}</p>
        {systolicComp ? (
          <p><strong>Systolický tlak:</strong> {systolicComp.valueQuantity?.value} {systolicComp.valueQuantity?.unit || 'N/A'}</p>
        ) : null}
        {diastolicComp ? (
          <p><strong>Diastolický tlak:</strong> {diastolicComp.valueQuantity?.value} {diastolicComp.valueQuantity?.unit || 'N/A'}</p>
        ) : null}
        {!systolicComp && !diastolicComp && (
          <p>Specifické komponenty pro krevní tlak nebyly nalezeny.</p>
        )}
      </div>
    );
  }

  // Generické zobrazení pro ostatní typy observací (Pulz, Teplota, Výška, Hmotnost)
  // Vychází z předpokladu, že mají podobnou strukturu valueQuantity
  if (["Pulz", "Tělesná teplota", "Tělesná výška", "Tělesná hmotnost"].includes(observationText)) {
    return (
      <div className="observation-data">
        <h4>Pozorování: {observationText} (ID: {observationId})</h4>
        <p><strong>Datum a čas měření:</strong> {effectiveDateTime}</p>
        <p><strong>Hodnota:</strong> {value}</p>
        <p><strong>Jednotka:</strong> {unit}</p>
      </div>
    );
  }

  // Fallback pro jiné typy Observation, které nemají specifické zobrazení
  return (
    <div className="observation-data">
      <h4>Pozorování: {observationText} (ID: {observationId})</h4>
      <p><strong>Datum a čas měření:</strong> {effectiveDateTime}</p>
      {resource.valueString && <p><strong>Hodnota (text):</strong> {resource.valueString}</p>}
      {resource.valueQuantity && <p><strong>Hodnota:</strong> {value} {unit}</p>}
      {/* Zde by se mohly přidat další běžná pole z Observation, pokud je to potřeba */}
      <details>
        <summary>Zobrazit kompletní data zdroje</summary>
        <pre style={{ maxHeight: '200px', overflowY: 'auto', backgroundColor: '#f5f5f5', border: '1px solid #ddd', padding: '5px' }}>
          {JSON.stringify(resource, null, 2)}
        </pre>
      </details>
    </div>
  );
};

export default ObservationCard;
