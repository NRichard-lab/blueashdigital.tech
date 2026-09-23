import { useEffect } from "react";
import { LibraryPreview } from "./library";
import { ReelLogo, SiteFrame, usePageMeta } from "./chrome";
import { products } from "./products";
import type { MarketingPage } from "./routes";

const homeDescription = "Blue Ash Digital builds thoughtful software around ownership, privacy, usefulness, and greater control over your digital life.";
const reelDescription = "Blue Ash Reel is a Blue Ash Digital product in development: a personal media platform for a library that stays at home, with built-in privacy and only essential data collected.";

export function Marketing({ page, focus, signedIn }: { page: MarketingPage; focus: string | null; signedIn: boolean }) {
  useEffect(() => {
    if (!focus) return;
    document.getElementById(focus)?.scrollIntoView();
  }, [focus, page]);

  if (page === "reel") return <ReelPage />;
  if (page === "support") return <SupportPage />;
  if (page === "privacy") return <NoticePage kind="privacy" />;
  if (page === "terms") return <NoticePage kind="terms" />;
  if (page === "not-found") return <NotFoundPage />;
  return <HomePage signedIn={signedIn} />;
}

function HomePage({ signedIn }: { signedIn: boolean }) {
  usePageMeta("Blue Ash Digital", homeDescription, "/");
  const product = products[0];

  return (
    <SiteFrame surface="dark" current={signedIn ? "portal" : "home"}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Organization",
        name: "Blue Ash Digital",
        url: "https://blueashdigital.tech/",
        description: homeDescription,
        logo: "https://blueashdigital.tech/brand/favicon.svg",
      }) }} />
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Independent technology studio</p>
          <h1>Technology that puts you back in control.</h1>
          <p className="lede">Blue Ash Digital builds thoughtful software around ownership, privacy, usefulness, and greater control over your digital life.</p>
          <div className="action-row">
            <a className="btn btn-cream" href="/products/blue-ash-reel">Explore Blue Ash Reel</a>
            <a className="btn btn-ghost-light" href="/#building">What We’re Building</a>
          </div>
          <p className="cue">Blue Ash Reel is the first branch. More thoughtful products will grow here.</p>
        </div>
        <div className="hero-tree">
          <img src="/brand/tree.png" alt="A mature ash tree with its roots visible beneath it." width={620} height={580} fetchPriority="high" />
          <img className="hero-roots" src="/brand/roots.svg" alt="" />
        </div>
      </section>

      <section className="band" id="products">
        <div className="section-intro">
          <p className="eyebrow">What we’re building</p>
          <h2>Growing from Blue Ash</h2>
          <p>One shared foundation, designed to support a family of useful products over time.</p>
        </div>
        {product ? (
          <article className="product-showcase">
            <div className="product-copy">
              <p className="status-line"><img src="/brand/status-dot.svg" alt="" width={8} height={8} /> {product.status}</p>
              <h3>{product.name}</h3>
              <p>{product.summary}</p>
              <p>{product.detail}</p>
              <a className="text-link" href={product.href}>{product.linkLabel} →</a>
            </div>
            <LibraryPreview />
          </article>
        ) : null}
        <p className="future-note">The shared foundation is ready for future products — without inventing them before they’re useful.</p>
      </section>

      <section className="band band-mist">
        <div className="section-intro wide">
          <p className="eyebrow">Why Blue Ash</p>
          <h2>Built from principles, not trends.</h2>
        </div>
        <div className="principle-grid">
          <article>
            <p>01 — leaf / root</p>
            <h3>Strong Roots</h3>
            <p>Software should have a solid technical foundation.</p>
          </article>
          <article className="principle-contrast">
            <p>02 — leaf / root</p>
            <h3>Protected by Design</h3>
            <p>Privacy belongs in the architecture.</p>
          </article>
          <article>
            <p>03 — leaf / root</p>
            <h3>Built to Grow</h3>
            <p>Products should evolve without abandoning people.</p>
          </article>
          <article>
            <p>04 — leaf / root</p>
            <h3>Yours</h3>
            <p>Technology should respect ownership and control.</p>
          </article>
        </div>
      </section>

      <section className="split-band">
        <div>
          <p className="eyebrow">Humanist software craft</p>
          <h2>Useful first. Quietly capable.</h2>
        </div>
        <div className="split-copy">
          <p>We focus on software that earns a place in everyday life: considered, legible, durable, and respectful of the person using it.</p>
          <p>No attention traps. No unnecessary collection. No claim that technology should replace human judgment.</p>
        </div>
      </section>

      <section className="band band-navy" id="building">
        <div className="section-intro wide">
          <p className="eyebrow">Open development</p>
          <h2>We’re building this now.</h2>
          <p>Blue Ash Digital is an independent project actively being designed, tested, and improved, with features evolving toward release.</p>
        </div>
        <ol className="lifecycle">
          <li><strong>Research</strong><span>Foundation complete</span></li>
          <li className="is-current"><strong>In Development</strong><span>Blue Ash Reel is here now</span></li>
          <li><strong>Testing</strong><span>Ahead</span></li>
          <li><strong>Available</strong><span>Ahead</span></li>
        </ol>
      </section>

      <section className="split-band about-band" id="about">
        <div>
          <p className="eyebrow">About Blue Ash Digital</p>
          <blockquote>Good technology should work for the people using it, not the other way around.</blockquote>
        </div>
        <div className="split-copy">
          <p>Blue Ash Digital builds practical software where privacy, ownership, usability, and technology work together.</p>
          <p>Like a mature tree, the company is designed around strong shared roots: patient engineering, clear choices, and products that can grow without losing sight of people.</p>
        </div>
      </section>

      <section className="callout">
        <h2>The first branch is taking shape.</h2>
        <a className="btn btn-cream" href="/products/blue-ash-reel">Explore Blue Ash Reel</a>
      </section>
    </SiteFrame>
  );
}

function ReelPage() {
  usePageMeta("Blue Ash Reel — Blue Ash Digital", reelDescription, "/products/blue-ash-reel");

  return (
    <SiteFrame surface="light" current="products">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Blue Ash Reel",
        description: reelDescription,
        url: "https://blueashdigital.tech/products/blue-ash-reel",
        isPartOf: { "@type": "WebSite", name: "Blue Ash Digital", url: "https://blueashdigital.tech/" },
      }) }} />
      <section className="product-hero">
        <div className="product-identity">
          <ReelLogo surface="light" />
          <p className="badge">In Development</p>
        </div>
        <div className="product-hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">A Blue Ash Digital product</p>
            <h1>Your media. Your library. Your home.</h1>
            <p className="lede">Your personal media, beautifully organized and ready to share, all in one place. Your library stays at home, with built-in privacy and only essential data collected.</p>
            <div className="action-row">
              <a className="btn btn-accent" href="/#building">Follow Development</a>
              <a className="btn btn-ghost-dark" href="https://blueashreel.com/login">Sign In</a>
            </div>
            <p className="cue">Your own media—not another streaming subscription.</p>
          </div>
          <LibraryPreview />
        </div>
      </section>

      <section className="ownership">
        <div className="storage-card">
          <p>Your home · local library</p>
          <ul>
            <li>Media files</li>
            <li>Artwork & organization</li>
            <li>Viewing information</li>
          </ul>
        </div>
        <div>
          <p className="eyebrow">Ownership first</p>
          <h2>Your media stays home.</h2>
          <p>Files, artwork, and viewing information remain centered on storage you control. Reel is designed around your library—not around moving it into someone else’s catalog.</p>
        </div>
      </section>

      <section className="watch-band">
        <div>
          <p className="eyebrow">Thoughtful presentation</p>
          <h2>Watch beautifully.</h2>
          <p>Movies and shows become a polished, navigable library with artwork, collections, and clear context—without losing the feeling that it is yours.</p>
        </div>
        <LibraryPreview />
      </section>

      <section className="band band-mist">
        <div className="section-intro wide">
          <p className="eyebrow">Personal by default</p>
          <h2>Share with the people you choose.</h2>
        </div>
        <div className="share-grid">
          <article>
            <h3>Household access</h3>
            <p>Invite the people close to you into a private, familiar viewing experience.</p>
          </article>
          <article>
            <h3>Clear permission</h3>
            <p>Choose who can connect without turning your library into a public cloud service.</p>
          </article>
          <article>
            <h3>Still yours</h3>
            <p>Sharing changes access—not ownership, storage, or the character of your collection.</p>
          </article>
        </div>
      </section>

      <section className="devices">
        <div className="section-intro">
          <p className="eyebrow">Flexible access</p>
          <h2>Works across devices.</h2>
          <p>TV, browser, and computer access are part of the concept, giving your personal library a consistent place across the screens you use.</p>
        </div>
        <div className="device-grid">
          <figure className="device-tv">
            <LibraryPreview compact />
            <figcaption>Television concept</figcaption>
          </figure>
          <figure className="device-browser">
            <LibraryPreview compact />
            <figcaption>Browser / computer concept</figcaption>
          </figure>
        </div>
      </section>

      <section className="privacy-band">
        <div>
          <p className="eyebrow">Privacy by design</p>
          <h2>Only what’s necessary leaves your system.</h2>
        </div>
        <div className="privacy-cards">
          <article>
            <h3>Stays with you</h3>
            <p>Media files, artwork, and viewing activity remain with the library you control.</p>
          </article>
          <article>
            <h3>Essential connection data</h3>
            <p>Only necessary account and connection information leaves your system.</p>
          </article>
        </div>
      </section>

      <section className="follow-band">
        <div>
          <p className="eyebrow">Actively in development</p>
          <h2>Follow the branch as it grows.</h2>
          <p>Blue Ash Reel is being designed, tested, and refined now. Capabilities may evolve as the product moves toward release.</p>
        </div>
        <a className="btn btn-accent" href="/#building">Follow Development</a>
      </section>

      <section className="callout callout-blue">
        <h2>A personal library should feel personal.</h2>
        <a className="btn btn-cream" href="https://blueashreel.com/login">Sign In</a>
      </section>
    </SiteFrame>
  );
}

function SupportPage() {
  usePageMeta("Support — Blue Ash Digital", "Support for Blue Ash Digital. Blue Ash Reel is in development, and documentation will be published when it is available.", "/support");
  return (
    <SiteFrame surface="light" current="support">
      <article className="text-page">
        <p className="eyebrow">Blue Ash Digital</p>
        <h1>Help for what exists today.</h1>
        <p>Blue Ash Reel is in development, so product documentation is not published yet. If you already have a development or testing account, you can sign in. New accounts are created by an administrator.</p>
        <div className="action-row">
          <a className="btn btn-accent" href="/signin">Sign In</a>
          <a className="btn btn-ghost-dark" href="/products/blue-ash-reel">Blue Ash Reel</a>
        </div>
        <h2 id="documentation">Documentation</h2>
        <p>Documentation will be added here when a product is available.</p>
      </article>
    </SiteFrame>
  );
}

function NoticePage({ kind }: { kind: "privacy" | "terms" }) {
  const privacy = kind === "privacy";
  usePageMeta(
    privacy ? "Privacy — Blue Ash Digital" : "Terms — Blue Ash Digital",
    privacy
      ? "Blue Ash Digital has not published a formal privacy policy yet. Sign-in uses only essential account and connection information."
      : "Blue Ash Digital has not published formal terms of use yet. Portal accounts are created by an administrator.",
    privacy ? "/privacy" : "/terms",
  );
  return (
    <SiteFrame surface="light" current={kind}>
      <article className="text-page">
        <p className="eyebrow">Legal</p>
        <h1>{privacy ? "Privacy" : "Terms"}</h1>
        {privacy ? (
          <>
            <p>A formal privacy policy is not published yet.</p>
            <p>Signing in uses only essential account and connection information. Blue Ash Reel, still in development, is designed so a personal library stays at home.</p>
          </>
        ) : (
          <>
            <p>Formal terms of use are not published yet.</p>
            <p>The application portal is for accounts an administrator has already created. There is no public registration.</p>
          </>
        )}
      </article>
    </SiteFrame>
  );
}

function NotFoundPage() {
  usePageMeta("Page not found — Blue Ash Digital", "That page is not part of the Blue Ash Digital site.", "/404");
  return (
    <SiteFrame surface="light" current="">
      <article className="text-page">
        <p className="eyebrow">Blue Ash Digital</p>
        <h1>That page is not here.</h1>
        <p>The address does not match a page on this site.</p>
        <a className="btn btn-accent" href="/">Back to the homepage</a>
      </article>
    </SiteFrame>
  );
}
