// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

// Define sample FHIR bundle at the top level
const sampleFhirBundle = {
  resourceType: "Bundle",
  id: "bundle-example-ui-simulated",
  type: "collection",
  entry: [
    {
      fullUrl: "Patient/pac-karelnovot-19750320",
      resource: {
        resourceType: "Patient",
        id: "pac-karelnovot-19750320",
        meta: {
          profile: [
            "https://ncez.mzcr.cz/fhir/core/StructureDefinition/CzPatient"
          ]
        },
        name: [{
          use: "official",
          given: ["Karel"],
          family: "Novotný"
        }],
        birthDate: "1975-03-20"
      }
    },
    {
      fullUrl: "Observation/obs-pac-karelnovot-19750320-bp1",
      resource: {
        resourceType: "Observation",
        id: "obs-pac-karelnovot-19750320-bp1",
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
          reference: "Patient/pac-karelnovot-19750320"
        },
        effectiveDateTime: "2024-07-25T10:30:00Z",
        component: [
          {
            code: {
              coding: [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}],
              text: "Systolický krevní tlak"
            },
            valueQuantity: {"value": 130, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
          },
          {
            code: {
              coding: [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}],
              text: "Diastolický krevní tlak"
            },
            valueQuantity: {"value": 85, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
          }
        ]
      }
    }
  ]
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

  // New function to get simulated FHIR data
  const getSimulatedFhirData = (textInput) => {
    console.log("Simulating FHIR data generation for text:", textInput);
    return sampleFhirBundle;
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
        {fhirOutput && (
          <section className="fhir-output-section">
            <h3>Strukturovaná FHIR Data (Simulace):</h3>
            <pre>{JSON.stringify(fhirOutput, null, 2)}</pre>
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
