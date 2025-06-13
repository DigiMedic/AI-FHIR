// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

/**
 * Hlavní komponenta aplikace AI-FHIR.
 * Umožňuje nahrání textového nebo obrázkového souboru a zobrazení "extrahovaného" obsahu.
 */
function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [error, setError] = useState('');
  const [fhirOutput, setFhirOutput] = useState(null);
  const [isLoadingFhir, setIsLoadingFhir] = useState(false); // State for loading indicator


  // New function to fetch FHIR data from backend
  const fetchFhirDataFromBackend = async (textInput) => {
    console.log("Requesting FHIR data from backend for text:", textInput);
    setIsLoadingFhir(true);
    setError(''); // Clear previous errors specifically for FHIR fetching
    try {
      const response = await fetch('http://localhost:8000/api/process_text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: textInput }),
      });

      if (!response.ok) {
        // Try to get error message from backend response body
        let errorMsg = `Chyba při komunikaci s backendem: ${response.status} ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorMsg = errorData.detail || errorMsg;
        } catch (e) {
            // Ignore if response is not JSON or empty
        }
        throw new Error(errorMsg);
      }

      const resources = await response.json();

      if (!resources || resources.length === 0) {
        console.log("Backend vrátil prázdná nebo žádná FHIR data.");
        setFhirOutput({ // Set fhirOutput to indicate no data, but not an error
            resourceType: "Bundle",
            id: "bundle-empty-from-backend",
            type: "collection",
            entry: []
        });
        return null; // Explicitly return null or an empty bundle structure
      }

      const bundle = {
        resourceType: "Bundle",
        id: "bundle-from-backend",
        type: "collection",
        entry: resources.map(resource => ({
          fullUrl: `${resource.resourceType}/${resource.id}`,
          resource: resource
        }))
      };
      return bundle;

    } catch (err) {
      console.error("Chyba při získávání FHIR dat z backendu:", err);
      setError(`Chyba při získávání FHIR dat: ${err.message}`);
      setFhirOutput(null); // Clear FHIR output on error
      return null; // Ensure null is returned on error
    } finally {
      setIsLoadingFhir(false);
    }
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
  const handleFileChange = async (event) => { // handleFileChange is now async
    const file = event.target.files[0];
    setError('');
    setExtractedText('');
    setFhirOutput(null);

    if (file) {
      setSelectedFile(file);

      let textForFhirProcessing = '';

      if (file.type === "text/plain") {
        try {
            const content = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = (e) => {
                    console.error("Chyba při čtení textového souboru:", e);
                    setError("Došlo k chybě při čtení textového souboru.");
                    reject(new Error("Chyba při čtení souboru"));
                };
                reader.readAsText(file);
            });
            textForFhirProcessing = simulateExtraction(content, file.type);
            setExtractedText(textForFhirProcessing);
        } catch (readError) {
            setSelectedFile(null);
            setFhirOutput(null);
            // Error already set by reader.onerror
            return; // Stop processing
        }
      } else if (file.type.startsWith("image/")) {
        textForFhirProcessing = simulateExtraction(null, file.type);
        setExtractedText(textForFhirProcessing);
      } else {
        setError("Prosím, nahrajte platný textový (.txt) nebo obrázkový (.png, .jpg, .jpeg) soubor.");
        setSelectedFile(null);
        setFhirOutput(null);
        event.target.value = null;
        return; // Stop processing
      }

      // Fetch FHIR data from backend if text was successfully extracted/simulated
      if (textForFhirProcessing) {
        const backendFhirData = await fetchFhirDataFromBackend(textForFhirProcessing);
        if (backendFhirData) {
            setFhirOutput(backendFhirData);
        } else if (!error) { // If fetchFhirDataFromBackend returned null but didn't set an error (e.g. empty resources)
            // Ensure fhirOutput is set to something that indicates no data, if not already handled by fetchFhirDataFromBackend
             if (!fhirOutput) { // Check if fhirOutput wasn't set by fetchFhirDataFromBackend
                setFhirOutput({
                    resourceType: "Bundle", id: "bundle-no-data-after-fetch", type: "collection", entry: []
                });
            }
        }
      }

    } else {
      setSelectedFile(null);
      setFhirOutput(null);
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

        {isLoadingFhir && (
            <section className="loading-fhir-section">
                <p>Zpracovávám data a generuji FHIR...</p>
            </section>
        )}

        {fhirOutput && fhirOutput.entry && fhirOutput.entry.length > 0 ? (
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data (z Backendu):</h3>
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
                 {/* Basic display for other resource types */}
                {entry.resource.resourceType !== "Patient" && entry.resource.resourceType !== "Observation" && (
                    <div>
                        <h4>{entry.resource.resourceType}</h4>
                        <pre>{JSON.stringify(entry.resource, null, 2)}</pre>
                    </div>
                )}
              </div>
            ))}
          </section>
        ) : (
          fhirOutput && // Show this section only if fhirOutput is not null, but might have empty entry
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data (z Backendu):</h3>
            <p>Žádná strukturovaná FHIR data nebyla vygenerována nebo nalezena z backendu.</p>
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
