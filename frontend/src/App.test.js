import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';

test('renders main heading', () => {
  render(<App />);
  const headingElement = screen.getByText(/AI-FHIR Komponenta/i);
  expect(headingElement).toBeInTheDocument();
});

test('file input is present and allows file selection', () => {
  render(<App />);
  const fileInput = screen.getByLabelText(/Nahrání dokumentu/i, { selector: 'input[type="file"]' });
  expect(fileInput).toBeInTheDocument();

  const testFile = new File(['(dummy content)'], 'test.txt', { type: 'text/plain' });
  fireEvent.change(fileInput, { target: { files: [testFile] } });

  // For now, we're just checking if the event can be fired.
  // A more comprehensive test would mock fetch and check for UI updates.
  // We can check if the input's files property was updated.
  expect(fileInput.files[0]).toBe(testFile);
  expect(fileInput.files.length).toBe(1);
});
