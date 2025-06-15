import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// Helper function to create a mock file
const createMockFile = (name, type, content) => {
  return new File([content], name, { type });
};

describe('App Component Tests', () => {
  // Mock global fetch before each test
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  // Restore mocks after each test
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders initial UI elements correctly', () => {
    render(<App />);
    expect(screen.getByText(/AI-FHIR Komponenta/i)).toBeInTheDocument();
    expect(screen.getByText(/Nástroj pro strukturování zdravotních dat do FHIR formátu./i)).toBeInTheDocument();
    expect(screen.getByText(/Nahrajte .txt nebo obrázek \(.png, .jpg, .jpeg\)./i)).toBeInTheDocument();
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    expect(fileInput).toBeInTheDocument();
  });

  test('allows file selection and displays file information', () => {
    render(<App />);
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    const testFile = createMockFile('test-document.txt', 'text/plain', 'This is a test file.');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    expect(screen.getByText(`Název souboru: ${testFile.name}`)).toBeInTheDocument();
    expect(screen.getByText(`Typ souboru: ${testFile.type}`)).toBeInTheDocument();
    expect(screen.getByText(`Velikost souboru: ${testFile.size} bytes`)).toBeInTheDocument();
    expect(fileInput.files[0]).toBe(testFile);
    expect(fileInput.files.length).toBe(1);
  });

  test('displays error message on API failure', async () => {
    fetch.mockRejectedValueOnce(new Error('API Error: Failed to fetch'));

    render(<App />);
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    const testFile = createMockFile('error-trigger.txt', 'text/plain', 'Content to trigger error.');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Chyba při zpracování souboru: API Error: Failed to fetch/i)).toBeInTheDocument();
    });
  });

  const mockFhirData = {
    fhir_resources: [
      {
        resourceType: "Patient",
        id: "patient-1",
        name: [{ text: "Jan Novák" }],
        birthDate: "1980-01-01",
        gender: "male",
        identifier: [{ type: {text: "Rodné číslo"}, value: "800101/1234"}]
      },
      {
        resourceType: "Observation",
        id: "obs-1",
        code: { text: "Tělesná výška" },
        effectiveDateTime: "2023-01-15T09:30:00Z",
        valueQuantity: { value: 180, unit: "cm" }
      }
    ],
    quality_issues: []
  };

  test('processes data successfully and displays FHIR resources', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockFhirData,
    });

    render(<App />);
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    const testFile = createMockFile('fhir-data.txt', 'text/plain', 'Valid data for FHIR.');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Strukturovaná FHIR Data/i)).toBeInTheDocument();
    });

    // Check for Patient data
    expect(screen.getByText(/Jan Novák/i)).toBeInTheDocument();
    expect(screen.getByText(/1980-01-01/i)).toBeInTheDocument();
    expect(screen.getByText(/male/i)).toBeInTheDocument();
    expect(screen.getByText(/Rodné číslo: 800101\/1234/i)).toBeInTheDocument();


    // Check for Observation data
    expect(screen.getByText(/Tělesná výška/i)).toBeInTheDocument();
    expect(screen.getByText(/180 cm/i)).toBeInTheDocument();
  });

  const mockQualityIssuesData = {
    fhir_resources: [],
    quality_issues: [
      { level: "Warning", message: "Chybějící PSČ", field: "Patient.address.postalCode" },
      { level: "Error", message: "Neplatné datum", field: "Observation.effectiveDateTime", value: "invalid-date" }
    ]
  };

  test('displays quality issues when present in API response', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockQualityIssuesData,
    });

    render(<App />);
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    const testFile = createMockFile('quality-issues.txt', 'text/plain', 'Data with quality issues.');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Problémy s kvalitou dat/i)).toBeInTheDocument();
    });

    // Check for quality issue details
    expect(screen.getByText(/Warning: Chybějící PSČ \(pole: Patient.address.postalCode\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Error: Neplatné datum \(pole: Observation.effectiveDateTime, hodnota: invalid-date\)/i)).toBeInTheDocument();
  });
});

// --- Testy pro funkcionalitu návrhu korekcí ---
describe('Correction Suggestion Feature', () => {
  beforeEach(() => {
    // Clear all fetch mocks before each test in this suite
    global.fetch.mockClear();
  });

  const mockFileData = (fileName, fileType, issues = [], fhirResources = []) => {
    const file = new File(['dummy content for ' + fileName], fileName, { type: fileType });
    const processResponse = {
      ok: true,
      json: async () => ({
        fhir_resources: fhirResources,
        quality_issues: issues,
      }),
    };
    return { file, processResponse };
  };

  test('displays correction form when "Navrhnout korekci" is clicked', async () => {
    const issues = [
      { level: "Warning", message: "Chybějící PSČ", field: "Patient.address.postalCode", value: "123" },
    ];
    const { file, processResponse } = mockFileData('test.txt', 'text/plain', issues);

    global.fetch.mockResolvedValueOnce(processResponse); // Mock pro /api/process_document

    render(<App />);

    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Počkat na zobrazení quality issue
    await waitFor(() => {
      expect(screen.getByText(/Chybějící PSČ/i)).toBeInTheDocument();
    });

    // Najít a kliknout na tlačítko pro korekci
    const suggestButton = screen.getByTestId('suggest-correction-btn-0');
    fireEvent.click(suggestButton);

    // Ověřit, že se formulář zobrazil
    await waitFor(() => {
      // Hledáme podle labelu, který by měl být generován v CorrectionForm.js
      // Např. "Navrhovaná korekce pro "Patient.address.postalCode":"
      expect(screen.getByLabelText(/Navrhovaná korekce pro "Patient.address.postalCode":/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Komentář \(volitelné\):/i)).toBeInTheDocument();
    });

    // Ověřit, že se zobrazila původní hodnota (pokud je)
    expect(screen.getByDisplayValue(String(issues[0].value))).toBeInTheDocument();
  });

  test('successfully submits a correction and hides form', async () => {
    const issues = [
      { level: "Error", message: "Neplatná hodnota", field: "Observation.valueQuantity.value", value: "abc" },
    ];
    const { file, processResponse } = mockFileData('submit-test.txt', 'text/plain', issues);

    // První fetch pro process_document
    global.fetch.mockResolvedValueOnce(processResponse);

    // Druhý fetch pro suggest_correction
    const mockSuggestionResponse = {
      ok: true,
      json: async () => ({ message: "Návrh úspěšně odeslán.", suggestion_details: {fileName: file.name} }),
    };
    global.fetch.mockResolvedValueOnce(mockSuggestionResponse);

    render(<App />);

    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => screen.getByTestId('suggest-correction-btn-0'));
    fireEvent.click(screen.getByTestId('suggest-correction-btn-0'));

    // Počkat na formulář
    const suggestionInput = await screen.findByLabelText(/Navrhovaná korekce pro "Observation.valueQuantity.value":/i);
    const commentInput = screen.getByLabelText(/Komentář \(volitelné\):/i);
    const submitButton = screen.getByRole('button', { name: /Odeslat návrh/i });

    // Vyplnit a odeslat formulář
    fireEvent.change(suggestionInput, { target: { value: '123' } });
    fireEvent.change(commentInput, { target: { value: 'Numerická hodnota' } });
    fireEvent.click(submitButton);

    // Ověřit API volání
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2); // Jedno pro process_document, jedno pro suggest_correction
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/suggest_correction'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            originalIssue: {
              level: issues[0].level,
              message: issues[0].message,
              field: issues[0].field,
              value: String(issues[0].value),
            },
            suggestedValue: '123',
            fileName: file.name,
            comment: 'Numerická hodnota',
          }),
        })
      );
    });

    // Ověřit úspěšnou zprávu a skrytí formuláře
    expect(screen.getByText("Návrh úspěšně odeslán.")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Navrhovaná korekce pro "Observation.valueQuantity.value":/i)).not.toBeInTheDocument();
  });

  test('handles error when submitting correction', async () => {
    const issues = [
      { level: "Warning", message: "Nízký tlak", field: "Observation.component[0].valueQuantity.value", value: "80" },
    ];
    const { file, processResponse } = mockFileData('error-submit.txt', 'text/plain', issues);

    global.fetch.mockResolvedValueOnce(processResponse); // process_document
    global.fetch.mockResolvedValueOnce({ // suggest_correction - chyba
      ok: false,
      status: 500,
      json: async () => ({ detail: "Internal Server Error" }),
    });

    render(<App />);
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => screen.getByTestId('suggest-correction-btn-0'));
    fireEvent.click(screen.getByTestId('suggest-correction-btn-0'));

    const suggestionInput = await screen.findByLabelText(/Navrhovaná korekce pro "Observation.component\[0\].valueQuantity.value":/i);
    fireEvent.change(suggestionInput, { target: { value: '90' } });
    fireEvent.click(screen.getByRole('button', { name: /Odeslat návrh/i }));

    await waitFor(() => {
      expect(screen.getByText(/Internal Server Error/i)).toBeInTheDocument();
    });
    // Formulář by měl zůstat viditelný (nebo se chovat dle definice při chybě)
    expect(screen.getByLabelText(/Navrhovaná korekce pro "Observation.component\[0\].valueQuantity.value":/i)).toBeInTheDocument();
  });

  test('cancels correction form', async () => {
    const issues = [
      { level: "Info", message: "Poznámka", field: "Patient.telecom[0].value", value: "123456" },
    ];
    const { file, processResponse } = mockFileData('cancel-test.txt', 'text/plain', issues);
    global.fetch.mockResolvedValueOnce(processResponse);

    render(<App />);
    const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => screen.getByTestId('suggest-correction-btn-0'));
    fireEvent.click(screen.getByTestId('suggest-correction-btn-0'));

    // Ověřit, že formulář je viditelný
    const suggestionInput = await screen.findByLabelText(/Navrhovaná korekce pro "Patient.telecom\[0\].value":/i);
    expect(suggestionInput).toBeInTheDocument();

    // Kliknout na "Zrušit"
    fireEvent.click(screen.getByRole('button', { name: /Zrušit/i }));

    // Ověřit, že formulář zmizel
    await waitFor(() => {
      expect(screen.queryByLabelText(/Navrhovaná korekce pro "Patient.telecom\[0\].value":/i)).not.toBeInTheDocument();
    });
  });
});
