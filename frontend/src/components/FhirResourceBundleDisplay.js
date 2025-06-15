// frontend/src/components/FhirResourceBundleDisplay.js
import React from 'react';
import PatientCard from './PatientCard';
import ObservationCard from './ObservationCard';
import ConditionCard from './ConditionCard';
import GenericFhirResourceCard from './GenericFhirResourceCard';

const FhirResourceBundleDisplay = ({ fhirBundle }) => {
  if (!fhirBundle || !fhirBundle.entry || fhirBundle.entry.length === 0) {
    return (
      <section className="fhir-output-section">
        <h3>Strukturovaná FHIR Data (z Backendu):</h3>
        <p>Žádná strukturovaná FHIR data nebyla vygenerována nebo nalezena z backendu pro nahraný soubor.</p>
      </section>
    );
  }

  return (
    <section className="fhir-output-section">
      <h3>Strukturovaná FHIR Data (z Backendu):</h3>
      {fhirBundle.entry.map((entry, index) => {
        if (!entry.resource) {
          return (
            <div key={index} className="fhir-resource" style={{ marginBottom: '15px', padding: '10px', border: '1px solid #eee', backgroundColor: '#fff0f0' }}>
              <p>Chyba: Chybějící 'resource' v položce Bundle.</p>
              <pre>{JSON.stringify(entry, null, 2)}</pre>
            </div>
          );
        }

        const { resource } = entry;

        return (
          <div key={index} className="fhir-resource" style={{ marginBottom: '15px', padding: '10px', border: '1px solid #eee' }}>
            {resource.resourceType === "Patient" && <PatientCard resource={resource} />}
            {resource.resourceType === "Observation" && <ObservationCard resource={resource} />}
            {resource.resourceType === "Condition" && <ConditionCard resource={resource} />}

            {/* Fallback pro ostatní typy, které nemají specifickou kartu */}
            {resource.resourceType !== "Patient" &&
             resource.resourceType !== "Observation" &&
             resource.resourceType !== "Condition" && (
                <GenericFhirResourceCard resource={resource} />
            )}
          </div>
        );
      })}
    </section>
  );
};

export default FhirResourceBundleDisplay;
