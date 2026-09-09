import { describe, expect, it } from "vitest";

import english from "../../messages/en.json";
import turkish from "../../messages/tr.json";

describe("ride-form campus defaults", () => {
  it("names the Dudullu campus in both supported locales", () => {
    expect(english.page.student.rideForm.defaultDropoff).toBe("Doğuş University, Dudullu Campus");
    expect(turkish.page.student.rideForm.defaultDropoff).toBe("Doğuş Üniversitesi, Dudullu Kampüsü");
  });
});
