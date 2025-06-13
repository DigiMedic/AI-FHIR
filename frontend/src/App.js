// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

/**
 * Hlavní komponenta aplikace AI-FHIR.
 * Umožňuje nahrání textového nebo obrázkového souboru,
 * odeslání na backend pro zpracování (včetně OCR pro obrázky)
 * a zobrazení výsledných FHIR dat, včetně nově přidaných diagnóz (Condition).
 */
function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [extractedTextFromBackend, setExtractedTextFromBackend] = useState('');
  const [error, setError] = useState('');
  const [fhirOutput, setFhirOutput] = useState(null);
  const [isLoading, setIsLoading] = useState(false);


  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    setError('');
    setExtractedTextFromBackend('');
    setFhirOutput(null);
    setSelectedFile(null);

    if (!file) {
      return;
    }

    setSelectedFile(file);
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log(`Odesílání souboru ${file.name} (${file.type}) na backend...`);
      const response = await fetch('http://localhost:8000/api/process_document', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMsg = `Chyba při komunikaci s backendem: ${response.status} ${response.statusText}`;
        try {
            const errorData = await response.json();
            if (errorData && errorData.detail) {
                 errorMsg = `Chyba z backendu: ${errorData.detail}`;
            } else if (Array.isArray(errorData) && errorData.length === 0 && response.status !== 200) {
                errorMsg = `Backend vrátil neočekávanou prázdnou odpověď se statusem ${response.status}.`;
            }
        } catch (e) {
            console.warn("Nepodařilo se parsovat chybovou JSON odpověď z backendu:", e);
        }
        throw new Error(errorMsg);
      }

      const resources = await response.json();
      console.log("Přijata data z backendu:", resources);

      if (file.type.startsWith("image/")) {
        setExtractedTextFromBackend(`[OBRÁZEK ZPRACOVÁN BACKENDEM]: ${file.name} (OCR provedeno na serveru)`);
      } else if (file.type === "text/plain") {
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            setExtractedTextFromBackend(`[TEXTOVÝ SOUBOR ZPRACOVÁN BACKENDEM]: ${file.name}
Obsah (prvních 100 znaků):
${content.substring(0,100)}...`);
        };
        reader.readAsText(file.slice(0, 100));
      }

      if (!resources || resources.length === 0) {
        console.log("Backend vrátil prázdná nebo žádná FHIR data.");
        setFhirOutput({
            resourceType: "Bundle",
            id: "bundle-empty-from-backend",
            type: "collection",
            entry: []
        });
      } else {
        const bundle = {
          resourceType: "Bundle",
          id: "bundle-from-backend",
          type: "collection",
          entry: resources.map(resource => ({
            fullUrl: `${resource.resourceType}/${resource.id}`,
            resource: resource
          }))
        };
        setFhirOutput(bundle);
      }

    } catch (err) {
      console.error("Chyba při odesílání souboru nebo zpracování odpovědi z backendu:", err);
      setError(`Chyba při zpracování souboru: ${err.message}`);
      setFhirOutput(null);
    } finally {
      setIsLoading(false);
      if (event && event.target) {
          event.target.value = null;
      }
    }
  };

  // Helper funkce pro formátování data a času
  const formatFhirDateTime = (dateTimeString) => {
    if (!dateTimeString) return 'N/A';
    try {
      // Zkusíme parsovat jako plné ISO datum a čas
      const date = new Date(dateTimeString);
      if (isNaN(date.getTime())) { // Pokud je neplatné, zkusíme jen jako datum (YYYY-MM-DD)
          const parts = dateTimeString.split('-');
          if (parts.length === 3) {
              const year = parseInt(parts[0]);
              const month = parseInt(parts[1]) -1; // Měsíce jsou 0-indexované v JS Date
              const day = parseInt(parts[2]);
              const simpleDate = new Date(year, month, day);
               if (!isNaN(simpleDate.getTime())) {
                   return simpleDate.toLocaleDateString('cs-CZ');
               }
          }
          return dateTimeString; // Vrátit původní string, pokud ani to nepomůže
      }
      return date.toLocaleString('cs-CZ');
    } catch (e) {
      console.warn("Chyba při formátování data:", dateTimeString, e);
      return dateTimeString; // V případě chyby vrátit původní řetězec
    }
  };


  return (
    <div className="App">
      <header className="App-header">
        <h1>AI-FHIR Komponenta</h1>
        <p>Nástroj pro strukturování zdravotních dat do FHIR formátu.</p>
        <p>Nahrajte .txt nebo obrázek (.png, .jpg, .jpeg).</p>
      </header>
      <main>
        <section className="upload-section">
          <h2>Nahrání dokumentu</h2>
          <input type="file" accept=".txt,image/png,image/jpeg,image/jpg" onChange={handleFileChange} disabled={isLoading} />
          {isLoading && <p className="loading-message">Zpracovávám soubor, prosím čekejte...</p>}
          {error && <p className="error-message">{error}</p>}
        </section>

        {selectedFile && !isLoading && (
          <section className="file-info-section">
            <h3>Informace o nahraném souboru:</h3>
            <p><strong>Název:</strong> {selectedFile.name}</p>
            <p><strong>Typ:</strong> {selectedFile.type}</p>
            <p><strong>Velikost:</strong> {selectedFile.size} bytů</p>
          </section>
        )}

        {extractedTextFromBackend && !isLoading && (
          <section className="extracted-text-section">
            <h3>Stav zpracování souboru:</h3>
            <pre>{extractedTextFromBackend}</pre>
          </section>
        )}

        {fhirOutput && !isLoading && fhirOutput.entry && fhirOutput.entry.length > 0 ? (
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data (z Backendu):</h3>
            {fhirOutput.entry.map((entry, index) => (
              <div key={index} className="fhir-resource" style={{ marginBottom: '15px', padding: '10px', border: '1px solid #eee' }}>
                {/* --- Zobrazení Pacienta --- */}
                {entry.resource.resourceType === "Patient" && (
                  <div className="patient-data">
                    <h4>Pacient (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Jméno:</strong> {entry.resource.name?.[0]?.text || `${entry.resource.name?.[0]?.given?.join(' ') || ''} ${entry.resource.name?.[0]?.family || ''}`.trim() || 'N/A'}</p>
                    <p><strong>Datum narození:</strong> {formatFhirDateTime(entry.resource.birthDate)}</p>
                  </div>
                )}
                {/* --- Zobrazení Pozorování (Krevní tlak) --- */}
                {entry.resource.resourceType === "Observation" && entry.resource.code?.text === "Krevní tlak" && (
                  <div className="observation-data">
                    <h4>Pozorování: Krevní tlak (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Datum a čas měření:</strong> {formatFhirDateTime(entry.resource.effectiveDateTime)}</p>
                    {
                      (() => {
                        const systolicComp = entry.resource.component?.find(comp => comp.code?.coding?.[0]?.code === "8480-6");
                        const diastolicComp = entry.resource.component?.find(comp => comp.code?.coding?.[0]?.code === "8462-4");
                        const renderedComponents = [];

                        if (systolicComp) {
                          renderedComponents.push(
                            <p key="systolic"><strong>Systolický tlak:</strong> {systolicComp.valueQuantity?.value} {systolicComp.valueQuantity?.unit || 'N/A'}</p>
                          );
                        }
                        if (diastolicComp) {
                          renderedComponents.push(
                            <p key="diastolic"><strong>Diastolický tlak:</strong> {diastolicComp.valueQuantity?.value} {diastolicComp.valueQuantity?.unit || 'N/A'}</p>
                          );
                        }
                        if (renderedComponents.length === 0) {
                           renderedComponents.push(<p key="no_bp_data">Specifické komponenty pro krevní tlak nebyly nalezeny.</p>);
                        }
                        return renderedComponents;
                      })()
                    }
                  </div>
                )}
                {/* --- Zobrazení Pozorování (Pulz) --- */}
                {entry.resource.resourceType === "Observation" && entry.resource.code?.text === "Pulz" && (
                  <div className="observation-data">
                    <h4>Pozorování: Pulz (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Datum a čas měření:</strong> {formatFhirDateTime(entry.resource.effectiveDateTime)}</p>
                    <p><strong>Hodnota:</strong> {entry.resource.valueQuantity?.value || 'N/A'}</p>
                    <p><strong>Jednotka:</strong> {entry.resource.valueQuantity?.unit || 'N/A'}</p>
                  </div>
                )}
                {/* --- Zobrazení Pozorování (Tělesná teplota) --- */}
                {entry.resource.resourceType === "Observation" && entry.resource.code?.text === "Tělesná teplota" && (
                  <div className="observation-data">
                    <h4>Pozorování: Tělesná teplota (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Datum a čas měření:</strong> {formatFhirDateTime(entry.resource.effectiveDateTime)}</p>
                    <p><strong>Hodnota:</strong> {entry.resource.valueQuantity?.value || 'N/A'}</p>
                    <p><strong>Jednotka:</strong> {entry.resource.valueQuantity?.unit || 'N/A'}</p>
                  </div>
                )}
                {/* --- Zobrazení Pozorování (Tělesná výška) --- */}
                {entry.resource.resourceType === "Observation" && entry.resource.code?.text === "Tělesná výška" && (
                  <div className="observation-data">
                    <h4>Pozorování: Tělesná výška (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Datum a čas měření:</strong> {formatFhirDateTime(entry.resource.effectiveDateTime)}</p>
                    <p><strong>Hodnota:</strong> {entry.resource.valueQuantity?.value || 'N/A'}</p>
                    <p><strong>Jednotka:</strong> {entry.resource.valueQuantity?.unit || 'N/A'}</p>
                  </div>
                )}
                {/* --- Zobrazení Pozorování (Tělesná hmotnost) --- */}
                {entry.resource.resourceType === "Observation" && entry.resource.code?.text === "Tělesná hmotnost" && (
                  <div className="observation-data">
                    <h4>Pozorování: Tělesná hmotnost (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Datum a čas měření:</strong> {formatFhirDateTime(entry.resource.effectiveDateTime)}</p>
                    <p><strong>Hodnota:</strong> {entry.resource.valueQuantity?.value || 'N/A'}</p>
                    <p><strong>Jednotka:</strong> {entry.resource.valueQuantity?.unit || 'N/A'}</p>
                  </div>
                )}
                {/* --- Zobrazení Diagnózy (Condition) --- */}
                {entry.resource.resourceType === "Condition" && (
                  <div className="condition-data">
                    <h4>Diagnóza (ID: {entry.resource.id || 'N/A'})</h4>
                    <p><strong>Text diagnózy:</strong> {entry.resource.code?.text || 'N/A'}</p>
                    <p><strong>Datum záznamu:</strong> {formatFhirDateTime(entry.resource.recordedDate)}</p>
                    <p><strong>Klinický stav:</strong> {entry.resource.clinicalStatus?.coding?.[0]?.display || entry.resource.clinicalStatus?.coding?.[0]?.code || 'N/A'}</p>
                    <p><strong>Stav ověření:</strong> {entry.resource.verificationStatus?.coding?.[0]?.display || entry.resource.verificationStatus?.coding?.[0]?.code || 'N/A'}</p>
                  </div>
                )}
                {/* --- Generické zobrazení pro ostatní typy zdrojů --- */}
                {entry.resource.resourceType !== "Patient" &&
                 !(entry.resource.resourceType === "Observation" &&
                   (entry.resource.code?.text === "Krevní tlak" ||
                    entry.resource.code?.text === "Pulz" ||
                    entry.resource.code?.text === "Tělesná teplota" ||
                    entry.resource.code?.text === "Tělesná výška" ||
                    entry.resource.code?.text === "Tělesná hmotnost")) &&
                 entry.resource.resourceType !== "Condition" && (
                    <div>
                        <h4>Resource: {entry.resource.resourceType} (ID: {entry.resource.id || 'N/A'}) - Obecné zobrazení</h4>
                        <pre style={{maxHeight: '200px', overflowY: 'auto', backgroundColor: '#f5f5f5', border: '1px solid #ddd', padding: '5px'}}>
                            {JSON.stringify(entry.resource, null, 2)}
                        </pre>
                    </div>
                )}
              </div>
            ))}
          </section>
        ) : (
          fhirOutput && !isLoading &&
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data (z Backendu):</h3>
            <p>Žádná strukturovaná FHIR data nebyla vygenerována nebo nalezena z backendu pro nahraný soubor.</p>
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
