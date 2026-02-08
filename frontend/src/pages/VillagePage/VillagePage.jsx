// src/pages/VillagePage.jsx
import { useEffect, useState } from "react";
import PopulationCentreMap from "../../components/Map/Map";
import { useGame } from "../../context/GameContext";
import { apiFetch } from "../../../utils/api";
import styles from "./VillagePage.module.scss";

export default function VillagePage() {
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

  console.log("geojson:", geojson);
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>{geojson?.meta?.population_centre_name || "Activity timer"}</h1>
      </div>

      <div className={styles.content}>
        {geojson ? (
          <PopulationCentreMap geojson={geojson} width={600} height={300} />
        ) : (
          "Loading..."
        )}
      </div>
    </div>
  );
}
