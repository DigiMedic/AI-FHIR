// frontend/src/utils/formatters.js

export const formatFhirDateTime = (dateTimeString) => {
  if (!dateTimeString) return 'N/A';
  try {
    const date = new Date(dateTimeString);
    if (isNaN(date.getTime())) {
      const parts = dateTimeString.split('-');
      if (parts.length === 3) {
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]) - 1; // Měsíce jsou 0-indexované v JS Date
        const day = parseInt(parts[2]);
        const simpleDate = new Date(year, month, day);
        if (!isNaN(simpleDate.getTime())) {
          return simpleDate.toLocaleDateString('cs-CZ');
        }
      }
      return dateTimeString;
    }
    return date.toLocaleString('cs-CZ');
  } catch (e) {
    console.warn("Chyba při formátování data:", dateTimeString, e);
    return dateTimeString;
  }
};

export const formatGender = (genderCode) => {
  if (!genderCode) return 'N/A';
  switch (genderCode.toLowerCase()) {
    case 'male':
      return 'Muž';
    case 'female':
      return 'Žena';
    case 'other':
      return 'Jiné';
    case 'unknown':
      return 'Neznámé';
    default:
      return genderCode;
  }
};
