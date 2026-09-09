export const DUDULLU_CAMPUS = {
  code: "D.Kampus",
  scheduleLabel: "Dudullu",
  address: "Doğuş Üniversitesi, Dudullu Kampüsü",
  coordinates: { lat: 41.001, lng: 29.177 },
} as const;

export const DUDULLU_DEPOT = {
  id: DUDULLU_CAMPUS.code,
  ...DUDULLU_CAMPUS.coordinates,
} as const;
