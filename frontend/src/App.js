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
    // setSelectedFile(null); // Reset selected file - toto způsobí, že se nezobrazí info o souboru, pokud je tato řádka zde

    if (file) {
      setSelectedFile(file); // Nastavíme soubor hned, aby se zobrazily jeho informace

      if (file.type === "text/plain") {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target.result;
          const processedText = simulateExtraction(content, file.type);
          setExtractedText(processedText);
        };
        reader.onerror = (e) => {
          console.error("Chybaři čtení textového souboru:", e);
          setError("Došlo k chybě při čtení textového souboru.");
          setSelectedFile(null); // Resetovat, pokud dojde k chybě čtení
        };
        reader.readAsText(file);
      } else if (file.type.startsWith("image/")) {
        const processedText = simulateExtraction(null, file.type);
        setExtractedText(processedText);
      } else {
        setError("Prosím, nahrajte platný textový (.txt) nebo obrázkový (.png, .jpg, .jpeg) soubor.");
        setSelectedFile(null); // Resetovat, pokud typ souboru není podporován
        event.target.value = null; // Reset file inputu, aby bylo možné znovu vybrat stejný (nesprávný) soubor
      }
    } else {
      setSelectedFile(null); // Pokud uživatel zruší výběr souboru
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
      </main>
      <footer className="App-footer">
        <p>&copy; 2024 DigiMedic. Všechna práva vyhrazena.</p>
      </footer>
    </div>
  );
}

export default App;
