You read one legal contract and fill in 12 fields. Answer only with JSON that fits the schema.

Rules for every field:
1. quotes: copy the exact text from the contract, character for character. Do not fix spelling.
   Do not shorten with "...". Copy the shortest full sentence or clause that answers the field.
2. If the contract has nothing for a field, return no quotes and found false. Example:
   {"quotes": [], "found": false}. For a field with a value, value is null (or [] for parties).
3. found is true only if you give at least one quote.
4. Use only the contract. Do not guess.

Rules for values:
- agreement_date: the date of the contract as YYYY-MM-DD. If the day or month is missing, write
  YYYY-MM or YYYY.
- governing_law: only the state or country, like "New York" or "Ontario, Canada".
- parties: value has the legal name of each party that signs. quotes has each name and each short
  name the contract gives it, like "Company" or "Licensor".
- renewal_term: the length of each renewal, like "1 year".
- notice_period_to_terminate_renewal: the notice needed to stop a renewal, like "90 days".
- cap_on_liability: a short summary of the cap, like "fees paid in the last 12 months".

What each field means:
- parties: the two or more parties who signed the contract.
- agreement_date: the date of the contract.
- governing_law: which state or country's law governs the contract.
- non_compete: a party may not compete with the other party, or may not work in a certain place,
  business or technology.
- change_of_control: a party may end the contract, or must get consent or give notice, if the
  other party is bought, merged, or sells most of its assets.
- anti_assignment: consent or notice is needed to give the contract to a third party.
- renewal_term: the renewal term after the first term ends, including automatic renewals.
- notice_period_to_terminate_renewal: the notice needed to stop a renewal.
- cap_on_liability: a limit on how much a party must pay if it breaks the contract, or a time limit
  to bring claims.
- license_grant: one party gives the other a license.
- ip_ownership_assignment: intellectual property made by one party becomes the other party's
  property.
- non_transferable_license: a party may not transfer the license to a third party.