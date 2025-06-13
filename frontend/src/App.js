// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

// Regex definitions (JS)
const REGEX_PATIENT_NAME_JS = /Pacient:\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)/i;
const REGEX_BIRTH_DATE_JS = /Datum narození:\s*(\d{1,2}\.\d{1,2}\.\d{4})/;
const REGEX_BLOOD_PRESSURE_JS = /Krevní tlak:\s*(\d{2,3}\/\d{2,3})\s*mmHg/i;

// Helper function to format date to YYYY-MM-DD
const formatDate = (dateString) => {
  const parts = dateString.split('.');
  if (parts.length === 3) {
    const day = parts[0].padStart(2, '0');
    const month = parts[1].padStart(2, '0');
    const year = parts[2];
    return `${year}-${month}-${day}`;
  }
  return null; // Invalid date format
};

// Implement parsePatientDataJs(text)
const parsePatientDataJs = (text) => {
  const patientData = {};
  const nameMatch = text.match(REGEX_PATIENT_NAME_JS);
  if (nameMatch && nameMatch[1]) {
    patientData.jmeno = nameMatch[1].trim();
  }

  const birthDateMatch = text.match(REGEX_BIRTH_DATE_JS);
  if (birthDateMatch && birthDateMatch[1]) {
    const formattedDate = formatDate(birthDateMatch[1]);
    if (formattedDate) {
      patientData.datum_narozeni = formattedDate;
    } else {
      patientData.datum_narozeni_raw = birthDateMatch[1];
    }
  }
  console.log("DEBUG [FHIR Mapper JS]: Parsed patient data:", patientData);
  return patientData;
};

// Implement createFhirPatientResourceJs(patientData, patientId)
const createFhirPatientResourceJs = (patientData, patientId) => {
  if (!patientData || !patientData.jmeno || !patientData.datum_narozeni) {
    console.log("DEBUG [FHIR Mapper JS]: Insufficient data to create FHIR Patient resource.");
    return null;
  }

  const resource = {
    resourceType: "Patient",
    id: patientId,
    meta: {
      profile: [
        "https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzPatient"
      ]
    },
    name: [{
      use: "official",
      family: patientData.jmeno, // Default to full name as family
    }],
    birthDate: patientData.datum_narozeni
  };

  const nameParts = patientData.jmeno.split(' ');
  if (nameParts.length > 1) {
    resource.name[0].given = [nameParts.shift()]; // First part as given
    resource.name[0].family = nameParts.join(' '); // The rest as family
  } else {
    // If only one word, it's considered family name as per python logic (fallback)
    resource.name[0].family = patientData.jmeno;
  }

  console.log("DEBUG [FHIR Mapper JS]: Created FHIR Patient resource:", JSON.stringify(resource, null, 2));
  return resource;
};

// Implement parseObservationDataJs(text)
const parseObservationDataJs = (text) => {
  const observationData = {};
  const bpMatch = text.match(REGEX_BLOOD_PRESSURE_JS);
  if (bpMatch && bpMatch[1]) {
    observationData.krevni_tlak_hodnota = bpMatch[1];
    observationData.cas_mereni = new Date().toISOString();
  }
  console.log("DEBUG [FHIR Mapper JS]: Parsed observation data:", observationData);
  return observationData;
};

// Implement createFhirObservationResourceJs(observationData, patientReferenceId, observationId)
const createFhirObservationResourceJs = (observationData, patientReferenceId, observationId) => {
  if (!observationData || !observationData.krevni_tlak_hodnota) {
    console.log("DEBUG [FHIR Mapper JS]: Insufficient data to create FHIR Observation resource.");
    return null;
  }

  const parts = observationData.krevni_tlak_hodnota.split('/');
  if (parts.length !== 2) {
    console.error("DEBUG [FHIR Mapper JS]: Invalid blood pressure format:", observationData.krevni_tlak_hodnota);
    return null;
  }
  const systolic = parseInt(parts[0], 10);
  const diastolic = parseInt(parts[1], 10);

  if (isNaN(systolic) || isNaN(diastolic)) {
    console.error("DEBUG [FHIR Mapper JS]: Non-numeric blood pressure values:", observationData.krevni_tlak_hodnota);
    return null;
  }

  const resource = {
    resourceType: "Observation",
    id: observationId,
    meta: {
      profile: [
        "https://ncez.mzcr.cz/fhir/core/StructureDefinition/VitalSignsObservation"
      ]
    },
    status: "final",
    category: [{
      coding: [{
        system: "http://terminology.hl7.org/CodeSystem/observation-category",
        code: "vital-signs",
        display: "Vital Signs"
      }]
    }],
    code: {
      coding: [{
        system: "http://loinc.org",
        code: "85354-9",
        display: "Blood pressure panel with all children optional"
      }],
      text: "Krevní tlak"
    },
    subject: {
      reference: patientReferenceId
    },
    effectiveDateTime: observationData.cas_mereni || new Date().toISOString(),
    component: [
      {
        code: {
          coding: [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}],
          text: "Systolický krevní tlak"
        },
        valueQuantity: {"value": systolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
      },
      {
        code: {
          coding: [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}],
          text: "Diastolický krevní tlak"
        },
        valueQuantity: {"value": diastolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
      }
    ]
  };
  console.log("DEBUG [FHIR Mapper JS]: Created FHIR Observation resource:", JSON.stringify(resource, null, 2));
  return resource;
};

// Implement mapTextToFhirJs(text)
const mapTextToFhirJs = (text) => {
  const fhirResources = [];
  const patientDataExtracted = parsePatientDataJs(text);

  let patientFhirId = null;
  let patientResource = null;

  if (patientDataExtracted && patientDataExtracted.jmeno && patientDataExtracted.datum_narozeni) {
    const patientIdSuffix = patientDataExtracted.jmeno.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
    const birthDateSuffix = patientDataExtracted.datum_narozeni.replace(/-/g, '');
    patientFhirId = `pac-${patientIdSuffix.substring(0, 10)}-${birthDateSuffix}`;

    patientResource = createFhirPatientResourceJs(patientDataExtracted, patientFhirId);
    if (patientResource) {
      fhirResources.push(patientResource);
    }
  }

  if (patientResource) { // Only create observation if patient was created
    const observationDataExtracted = parseObservationDataJs(text);
    if (observationDataExtracted && observationDataExtracted.krevni_tlak_hodnota) {
      const observationFhirId = `obs-${patientFhirId}-bp1`;
      const observationResource = createFhirObservationResourceJs(
        observationDataExtracted,
        `Patient/${patientFhirId}`,
        observationFhirId
      );
      if (observationResource) {
        fhirResources.push(observationResource);
      }
    }
  }

  if (fhirResources.length === 0) {
    console.log("DEBUG [FHIR Mapper JS]: No FHIR resources were created from the given text.");
  }
  return fhirResources;
};


/**
 * Hlavní komponenta aplikace AI-FHIR.
 * Umožňuje nahrání textového nebo obrázkového souboru a zobrazení "extrahovaného" obsahu.
 */
function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [error, setError] = useState('');
  const [fhirOutput, setFhirOutput] = useState(null); // New state variable

  // Updated function to use mapTextToFhirJs
  const getSimulatedFhirData = (textInput) => {
    console.log("Generating FHIR data for text:", textInput);
    const resources = mapTextToFhirJs(textInput);

    if (!resources || resources.length === 0) {
      return null;
    }

    const bundle = {
      resourceType: "Bundle",
      id: "bundle-dynamic-ui", // Placeholder or dynamic ID
      type: "collection",
      entry: resources.map(resource => ({
        fullUrl: `${resource.resourceType}/${resource.id}`,
        resource: resource
      }))
    };
    return bundle;
  };

  /**
   * Simulovaná funkce pro extrakci textu nebo indikaci OCR zpracování.
   * @param {string} documentContent Obsah textového dokumentu nebo null pro obrázky.
   * @param {string} fileType Typ souboru ('text/plain', 'image/png', atd.).
   * @returns {string} "Extrahovaný" text nebo zpráva o OCR.
   */
  const simulateExtraction = (documentContent, fileType) => {
    // Musíme přistupovat k selectedFile přes stav, protože v momentě volání této funkce
    // nemusí být selectedFile v argumentu funkce aktuální, pokud se volá zevnitř jiné callback funkce.
    // Nicméně, pro jednoduchost zde ponecháme původní logiku, ale v reálné aplikaci by to mohlo vyžadovat úpravu.
    const currentFileName = selectedFile ? selectedFile.name : 'vybraný soubor';

    if (fileType === "text/plain") {
      if (typeof documentContent !== 'string') {
        console.error("Chyba: Vstupní dokument pro textovou extrakci musí být řetězec.");
        return "Chyba při zpracování: Vstupní dokument není text.";
      }
      const lowerCaseText = documentContent.toLowerCase();
      return `[ZÁKLADNÍ TEXTOVÁ EXTRAKCE JS]:\n${lowerCaseText}`;
    } else if (fileType && fileType.startsWith("image/")) {
      return `[SIMULACE OCR]: Soubor '${currentFileName}' by byl odeslán na server k OCR zpracování.\n(Skutečné OCR proběhne na backendu.)`;
    } else {
      return "Neznámý typ souboru pro extrakci nebo soubor nebyl správně detekován.";
    }
  };

  /**
   * Handler pro změnu ve file inputu.
   * Zpracuje nahraný soubor a spustí simulovanou extrakci.
   */
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setError('');
    setExtractedText('');
    setFhirOutput(null); // Reset FHIR output
    // setSelectedFile(null); // Reset selected file - toto způsobí, že se nezobrazí info o souboru, pokud je tato řádka zde

    if (file) {
      setSelectedFile(file); // Nastavíme soubor hned, aby se zobrazily jeho informace

      if (file.type === "text/plain") {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target.result;
          const processedText = simulateExtraction(content, file.type);
          setExtractedText(processedText);
          const simulatedFhir = getSimulatedFhirData(processedText);
          setFhirOutput(simulatedFhir);
        };
        reader.onerror = (e) => {
          console.error("Chybaři čtení textového souboru:", e);
          setError("Došlo k chybě při čtení textového souboru.");
          setSelectedFile(null); // Resetovat, pokud dojde k chybě čtení
          setFhirOutput(null);
        };
        reader.readAsText(file);
      } else if (file.type.startsWith("image/")) {
        const processedText = simulateExtraction(null, file.type);
        setExtractedText(processedText);
        const simulatedFhir = getSimulatedFhirData(processedText); // processedText here is the OCR simulation message
        setFhirOutput(simulatedFhir);
      } else {
        setError("Prosím, nahrajte platný textový (.txt) nebo obrázkový (.png, .jpg, .jpeg) soubor.");
        setSelectedFile(null); // Resetovat, pokud typ souboru není podporován
        setFhirOutput(null);
        event.target.value = null; // Reset file inputu, aby bylo možné znovu vybrat stejný (nesprávný) soubor
      }
    } else {
      setSelectedFile(null); // Pokud uživatel zruší výběr souboru
      setFhirOutput(null); // Also reset if user cancels file selection
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI-FHIR Komponenta</h1>
        <p>Nástroj pro strukturování zdravotních dat do FHIR formátu.</p>
      </header>
      <main>
        <section className="upload-section">
          <h2>Nahrání dokumentu</h2>
          <p>Vyberte textový (.txt) nebo obrázkový (.png, .jpg, .jpeg) soubor pro zpracování:</p>
          <input type="file" accept=".txt,image/png,image/jpeg,image/jpg" onChange={handleFileChange} />
          {error && <p className="error-message">{error}</p>}
        </section>

        {selectedFile && (
          <section className="file-info-section">
            <h3>Informace o nahraném souboru:</h3>
            <p><strong>Název:</strong> {selectedFile.name}</p>
            <p><strong>Typ:</strong> {selectedFile.type}</p>
            <p><strong>Velikost:</strong> {selectedFile.size} bytů</p>
          </section>
        )}

        {extractedText && (
          <section className="extracted-text-section">
            <h3>Výsledek zpracování:</h3>
            <pre>{extractedText}</pre>
          </section>
        )}

        {/* New section for FHIR data */}
        {fhirOutput && fhirOutput.entry && fhirOutput.entry.length > 0 ? (
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data:</h3>
            {fhirOutput.entry.map((entry, index) => (
              <div key={index} className="fhir-resource" style={{ marginBottom: '15px', padding: '10px', border: '1px solid #eee' }}>
                {entry.resource.resourceType === "Patient" && (
                  <div className="patient-data">
                    <h4>Pacient</h4>
                    <p><strong>Jméno:</strong> {entry.resource.name?.[0]?.given?.join(' ') || ''} {entry.resource.name?.[0]?.family || 'N/A'}</p>
                    <p><strong>Datum narození:</strong> {entry.resource.birthDate || 'N/A'}</p>
                  </div>
                )}
                {entry.resource.resourceType === "Observation" && (
                  <div className="observation-data">
                    <h4>Pozorování: Krevní tlak</h4>
                    <p><strong>Datum a čas měření:</strong> {entry.resource.effectiveDateTime ? new Date(entry.resource.effectiveDateTime).toLocaleString('cs-CZ') : 'N/A'}</p>
                    {
                      (() => {
                        const systolicComp = entry.resource.component?.find(comp => comp.code?.coding?.[0]?.code === "8480-6");
                        const diastolicComp = entry.resource.component?.find(comp => comp.code?.coding?.[0]?.code === "8462-4");
                        let componentsFound = false;

                        const renderedComponents = [];

                        if (systolicComp) {
                          componentsFound = true;
                          renderedComponents.push(
                            <p key="systolic"><strong>Systolický tlak:</strong> {systolicComp.valueQuantity?.value} {systolicComp.valueQuantity?.unit || 'N/A'}</p>
                          );
                        }
                        if (diastolicComp) {
                          componentsFound = true;
                          renderedComponents.push(
                            <p key="diastolic"><strong>Diastolický tlak:</strong> {diastolicComp.valueQuantity?.value} {diastolicComp.valueQuantity?.unit || 'N/A'}</p>
                          );
                        }

                        if (!componentsFound && entry.resource.component?.length > 0) {
                           renderedComponents.push(<p key="no_bp_data">Specifické komponenty pro systolický/diastolický tlak nebyly nalezeny.</p>);
                        } else if (!componentsFound) {
                           renderedComponents.push(<p key="no_components">Žádné komponenty měření k zobrazení.</p>);
                        }
                        return renderedComponents;
                      })()
                    }
                  </div>
                )}
              </div>
            ))}
          </section>
        ) : (
          fhirOutput && // Show this section only if fhirOutput is not null, but might have empty entry
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data:</h3>
            <p>Žádná strukturovaná FHIR data nebyla vygenerována nebo nalezena.</p>
          </section>
        )}
      </main>
      <footer className="App-footer">
        <p>&copy; 2024 DigiMedic. Všechna práva vyhrazena.</p>
      </footer>
    </div>
  );
}

export default App;
