import { ReelLogo } from "./chrome";

const titles = [
  { src: "/brand/title-quiet-harbor.png", name: "Quiet Harbor" },
  { src: "/brand/title-north-woods.png", name: "North Woods" },
  { src: "/brand/title-after-rain.png", name: "After Rain" },
  { src: "/brand/title-long-way.png", name: "The Long Way" },
];

export function LibraryPreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`library ${compact ? "library-compact" : ""}`}>
      <div className="library-top">
        <ReelLogo surface="dark" />
        <p>Mara’s Library · at home</p>
      </div>
      <div className="library-feature">
        <img src="/brand/poster.png" alt="" />
        <div>
          <p>Your collection</p>
          <p>Quiet Harbor</p>
        </div>
      </div>
      <ul className="library-row">
        {titles.map((title) => (
          <li key={title.name}>
            <img src={title.src} alt="" loading="lazy" />
            <span>{title.name}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
