// frontend/src/components/FileUploadSection.js
import React from 'react';

const FileUploadSection = ({ onFileChange, isLoading, selectedFile }) => {
  return (
    <section className="upload-section">
      <h2>Nahrání dokumentu</h2>
      <input
        type="file"
        accept=".txt,image/png,image/jpeg,image/jpg"
        onChange={onFileChange}
        disabled={isLoading}
      />
      {selectedFile && !isLoading && (
        <div className="file-info-preview" style={{marginTop: '10px'}}>
          <p><strong>Název vybraného souboru:</strong> {selectedFile.name}</p>
          <p><strong>Typ:</strong> {selectedFile.type}</p>
          <p><strong>Velikost:</strong> {selectedFile.size} bytů</p>
        </div>
      )}
    </section>
  );
};

export default FileUploadSection;
