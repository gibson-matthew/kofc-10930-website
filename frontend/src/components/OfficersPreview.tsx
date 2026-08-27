import { useOfficers } from "../hooks/useOfficers";

export default function OfficersPreview() {
  const { data } = useOfficers();

  if (!data) return <div>Loading officers...</div>;

  return (
    <div>
      <h2>Our Officers</h2>
      {data.map((officer: any) => (
        <div key={officer.id}>
          <p>{officer.position}</p>
          <p>Term: {officer.term_start} → {officer.term_end}</p>
        </div>
      ))}
    </div>
  );
}
