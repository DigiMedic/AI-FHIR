// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

// Import nově vytvořených komponent
import FileUploadSection from './components/FileUploadSection';
import ProcessingInfo from './components/ProcessingInfo';
import FhirResourceBundleDisplay from './components/FhirResourceBundleDisplay';
import QualityIssuesSection from './components/QualityIssuesSection';
import LoadingIndicator from './components/LoadingIndicator';
import ErrorMessage from './components/ErrorMessage';

// Import utilit (pokud by byly potřeba přímo v App.js, jinak jsou v komponentách)
// Např. pokud bychom chtěli nějaké formátování přímo zde.
// Prozatím nejsou explicitně potřeba, protože formátování je zapouzdřeno.

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [processingStatusText, setProcessingStatusText] = useState(''); // Přejmenováno z extractedTextFromBackend
  const [error, setError] = useState('');
  const [fhirOutput, setFhirOutput] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [qualityIssues, setQualityIssues] = useState([]);
  const [editingIssueIndex, setEditingIssueIndex] = useState(null);
  const [correctionSuggestion, setCorrectionSuggestion] = useState('');
  const [correctionComment, setCorrectionComment] = useState('');
  const [correctionStatus, setCorrectionStatus] = useState('');
  const [digimedicStatusMessage, setDigimedicStatusMessage] = useState(''); // Nový stav

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    setError('');
    setProcessingStatusText('');
    setFhirOutput(null);
    setQualityIssues([]);
    setSelectedFile(null);
    setEditingIssueIndex(null);
    setCorrectionSuggestion('');
    setCorrectionComment(''); // Již zde bylo z předchozího kroku
    setCorrectionStatus('');
    setDigimedicStatusMessage(''); // Reset DigiMedic statusu

    if (!file) {
      return;
    }

    setSelectedFile(file);
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log(`Odesílání souboru ${file.name} (${file.type}) na backend: ${API_URL}/api/process_document`);
      const response = await fetch(`${API_URL}/api/process_document`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMsg = `Chyba při komunikaci s backendem: ${response.status} ${response.statusText}`;
        try {
            const errorData = await response.json();
            if (errorData && errorData.detail) {
                 errorMsg = `Chyba z backendu: ${errorData.detail}`;
            } else if (errorData && Array.isArray(errorData.detail) && errorData.detail.length > 0 && errorData.detail[0].msg) {
                 errorMsg = `Chyba validace z backendu: ${errorData.detail[0].msg} (pole: ${errorData.detail[0].loc?.join('->') || 'N/A'})`;
            }
        } catch (e) {
            console.warn("Nepodařilo se parsovat chybovou JSON odpověď z backendu:", e);
        }
        throw new Error(errorMsg);
      }

      const responseData = await response.json();
      console.log("Přijata strukturovaná data z backendu:", responseData);

      if (responseData && typeof responseData === 'object' &&
          responseData.hasOwnProperty('fhir_resources') && responseData.hasOwnProperty('quality_issues')) {

        const fhir_resources = responseData.fhir_resources;
        const current_quality_issues = responseData.quality_issues;
        const digimedic_submission_status = responseData.digimedic_submission_status; // Zpracování nového klíče

        setQualityIssues(current_quality_issues || []);
        if (digimedic_submission_status) {
          setDigimedicStatusMessage(digimedic_submission_status);
        } else {
          // Fallback, pokud backend nevrátí status (pro starší verze nebo chybu)
          if (fhir_resources && fhir_resources.length > 0) { // Jen pokud se zdá, že se něco mohlo odesílat
            setDigimedicStatusMessage("Informace o odeslání na DigiMedic API nebyla explicitně poskytnuta backendem.");
          }
        }

        if (file.type.startsWith("image/")) {
          setProcessingStatusText(`[OBRÁZEK ZPRACOVÁN BACKENDEM]: ${file.name} (OCR provedeno na serveru)`);
        } else if (file.type === "text/plain") {
          const reader = new FileReader();
          reader.onload = (e) => {
              const content = e.target.result;
              setProcessingStatusText(`[TEXTOVÝ SOUBOR ZPRACOVÁN BACKENDEM]: ${file.name}
Obsah (prvních 100 znaků):
${content.substring(0,100)}...`);
          };
          reader.readAsText(file.slice(0, 100)); // Jen prvních 100 znaků pro zobrazení
        }

        if (!fhir_resources || fhir_resources.length === 0) {
          console.log("Backend vrátil prázdná nebo žádná FHIR data v klíči 'fhir_resources'.");
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
            type: "collection", // Nebo jiný typ, pokud backend specifikuje
            entry: fhir_resources.map(resource => ({
              fullUrl: resource && resource.resourceType && resource.id ? `${resource.resourceType}/${resource.id}` : `urn:uuid:${Math.random().toString(36).substr(2, 9)}`,
              resource: resource
            }))
          };
          setFhirOutput(bundle);
        }
      } else {
        console.error("Chybná struktura odpovědi z backendu:", responseData);
        setError('Chybná struktura odpovědi z backendu. Očekáván objekt s klíči "fhir_resources" a "quality_issues".');
        setFhirOutput(null);
        setQualityIssues([]);
      }

    } catch (err) {
      console.error("Chyba při odesílání souboru nebo zpracování odpovědi z backendu:", err);
      setError(`Chyba při zpracování souboru: ${err.message}`);
      setFhirOutput(null);
      setQualityIssues([]);
    } finally {
      setIsLoading(false);
      if (event && event.target) {
          event.target.value = null;
      }
    }
  };

  const handleStartCorrection = (index) => {
    setEditingIssueIndex(index);
    const issueValue = qualityIssues[index]?.value;
    setCorrectionSuggestion(issueValue !== undefined && issueValue !== null ? String(issueValue) : '');
    setCorrectionComment(''); // Reset komentáře při otevření nového formuláře
    setCorrectionStatus('');
  };

  const handleCancelCorrection = () => {
    setEditingIssueIndex(null);
    setCorrectionSuggestion('');
    setCorrectionComment(''); // Reset komentáře
  };

  const handleSuggestionChange = (event) => {
    setCorrectionSuggestion(event.target.value);
  };

  const handleCorrectionCommentChange = (event) => { // Nový handler
    setCorrectionComment(event.target.value);
  };

  const handleSubmitCorrection = async (index) => {
    const originalIssue = qualityIssues[index];
    if (!originalIssue) {
      setCorrectionStatus("Chyba: Původní problém s kvalitou nenalezen.");
      return;
    }

    const payload = {
      originalIssue: { // Struktura dle Pydantic modelu na backendu
        level: originalIssue.level,
        message: originalIssue.message,
        field: originalIssue.field || originalIssue.path, // Použijeme 'path', pokud 'field' není
        value: originalIssue.value !== undefined ? String(originalIssue.value) : null
      },
      suggestedValue: correctionSuggestion,
      fileName: selectedFile ? selectedFile.name : 'N/A',
      comment: correctionComment // Přidání komentáře do payloadu
    };

    setIsLoading(true);
    setCorrectionStatus('');

    try {
      const response = await fetch(`${API_URL}/api/suggest_correction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json(); // Zkusíme parsovat JSON vždy

      if (response.ok) {
        setCorrectionStatus(responseData.message || "Návrh úspěšně odeslán.");
      } else {
        let errorMsg = responseData.detail || `Chyba serveru: ${response.status}`;
        if (Array.isArray(responseData.detail) && responseData.detail.length > 0 && responseData.detail[0].msg) {
           errorMsg = `Chyba validace: ${responseData.detail[0].msg} (pro pole: ${responseData.detail[0].loc?.join('->') || 'N/A'})`;
        }
        setCorrectionStatus(errorMsg);
      }
    } catch (networkError) {
      console.error("Network error submitting correction:", networkError);
      setCorrectionStatus("Chyba sítě při odesílání návrhu.");
    } finally {
      setIsLoading(false);
      setEditingIssueIndex(null); // Ukončíme editaci po odeslání
    setCorrectionSuggestion('');
    setCorrectionComment('');
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
        <FileUploadSection
          onFileChange={handleFileChange}
          isLoading={isLoading}
          selectedFile={selectedFile}
        />

        {isLoading && <LoadingIndicator />}
        {error && <ErrorMessage message={error} />}

        {processingStatusText && !isLoading && (
          <ProcessingInfo processingStatusText={processingStatusText} />
        )}

        {fhirOutput && !isLoading && (
          <FhirResourceBundleDisplay fhirBundle={fhirOutput} />
        )}

        {/* Zobrazení DigiMedic statusu */}
        {digimedicStatusMessage && !isLoading && (
          <section className="digimedic-status-section info-section">
            <h3>Stav odeslání na DigiMedic API:</h3>
            <p className={
              digimedicStatusMessage.toLowerCase().includes("chyba") ||
              digimedicStatusMessage.toLowerCase().includes("selhalo") ||
              digimedicStatusMessage.toLowerCase().includes("nepodařilo")
              ? "status-message-error"
              : digimedicStatusMessage.toLowerCase().includes("úspěšně")
                ? "status-message-success"
                : "status-message-info"
            }>
              {digimedicStatusMessage}
            </p>
          </section>
        )}

        {/* Sekce pro Quality Issues se zobrazí vždy, pokud byl vybrán soubor a není loading */}
        {!isLoading && selectedFile && (
          <QualityIssuesSection
            issues={qualityIssues}
            correctionStatus={correctionStatus}
            editingIssueIndex={editingIssueIndex}
            correctionSuggestion={correctionSuggestion}
            correctionComment={correctionComment} // Předání nového stavu
            isLoading={isLoading}
            onStartCorrection={handleStartCorrection}
            onCancelCorrection={handleCancelCorrection}
            onSuggestionChange={handleSuggestionChange}
            onCorrectionCommentChange={handleCorrectionCommentChange} // Předání nového handleru
            onSubmitCorrection={handleSubmitCorrection}
          />
        )}
      </main>
      <footer className="App-footer">
        <p>&copy; 2024 DigiMedic. Všechna práva vyhrazena.</p>
      </footer>
    </div>
  );
}

export default App;
