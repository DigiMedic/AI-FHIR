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
