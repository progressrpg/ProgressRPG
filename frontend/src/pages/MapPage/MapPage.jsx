// src/pages/MapPage.jsx
import { useEffect, useState } from "react";
import PopulationCentreMap from "../../components/Map/Map";
import { useGame } from "../../context/GameContext";
import { apiFetch } from "../../../utils/api";

export default function MapPage() {
  const [geojson, setGeojson] = useState(null);
  const { character } = useGame();
  const pcId = character?.population_centre_id;
  //console.log("character:", character);
  //console.log("pcId:", pcId);

  useEffect(() => {
    if (pcId == null) return;

    const fetchData = async () => {
      try {
        const data = await apiFetch(`/population-centres/${pcId}/map/`);
        setGeojson(data);
      } catch (err) {
        console.error("Error fetching map:", err);
      }
    };

    fetchData();
  }, [pcId]);

  return (
    <div>
      {geojson ? (
        <PopulationCentreMap geojson={geojson} width={800} height={600} />
      ) : (
        "Loading..."
      )}
    </div>
  );
}
