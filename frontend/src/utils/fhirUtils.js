// frontend/src/utils/fhirUtils.js

export const findRodneCislo = (identifiers) => {
  if (!identifiers || !Array.isArray(identifiers)) {
    return 'N/A';
  }
  const rodneCisloIdentifier = identifiers.find(id => {
    if (!id || !id.type) return false;

    const typeTextMatch = id.type.text === "Rodné číslo";
    const hasNICode = Array.isArray(id.type.coding) &&
                      id.type.coding.some(coding => coding.code === "NI" && coding.system === "http://terminology.hl7.org/CodeSystem/v2-0203");
    const systemIsRCOID = id.system === "urn:oid:1.2.203.17.4.1";

    if (typeTextMatch && systemIsRCOID) return true;
    if (hasNICode && systemIsRCOID) return true;
    if (typeTextMatch && !systemIsRCOID) return true; // Fallback

    return false;
  });

  return rodneCisloIdentifier ? rodneCisloIdentifier.value : 'N/A';
};
