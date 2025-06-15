// frontend/src/components/GenericFhirResourceCard.js
import React from 'react';

const GenericFhirResourceCard = ({ resource }) => {
  if (!resource) {
    return <p>Chybějící data pro FHIR resource.</p>;
  }

  return (
    <div>
      <h4>Resource: {resource.resourceType} (ID: {resource.id || 'N/A'}) - Obecné zobrazení</h4>
      <pre style={{ maxHeight: '200px', overflowY: 'auto', backgroundColor: '#f5f5f5', border: '1px solid #ddd', padding: '5px' }}>
        {JSON.stringify(resource, null, 2)}
      </pre>
    </div>
  );
};

export default GenericFhirResourceCard;
