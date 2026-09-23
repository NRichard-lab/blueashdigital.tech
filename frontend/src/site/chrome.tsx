import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { products } from "./products";

type Surface = "dark" | "light";

export function Logo({ surface }: { surface: Surface }) {
  const onDark = surface === "dark";
  return (
    <a className={`logo ${onDark ? "logo-on-dark" : "logo-on-light"}`} href="/">
      <span className="logo-mark">
        <img src={onDark ? "/brand/leaf-on-light.svg" : "/brand/leaf-on-dark.svg"} alt="" width={19} height={24} />
      </span>
      <span className="logo-words">
        <span className="logo-name">Blue Ash</span>
        <span className="logo-descriptor">Digital</span>
      </span>
    </a>
  );
}

export function ReelLogo({ surface }: { surface: Surface }) {
  const onDark = surface === "dark";
  return (
    <span className={`logo reel-logo ${onDark ? "logo-on-dark" : "logo-on-light"}`}>
      <a className="reel-mark-link" href="https://blueashreel.com/">
        <img className="reel-mark" src="/brand/reel-leaf.png" alt="Blue Ash Reel" width={42} height={47} />
      </a>
      <span className="logo-words">
        <span className="logo-name">Blue Ash</span>
        <span className="logo-descriptor">Reel</span>
      </span>
    </span>
  );
}

const links = [
  { href: "/#products", label: "Products", id: "products" },
  { href: "/#about", label: "About", id: "about" },
  { href: "/#building", label: "What’s Building", id: "building" },
  { href: "/support", label: "Support", id: "support" },
];

export function SiteHeader({ surface, current }: { surface: Surface; current: string }) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const toggle = toggleRef.current;
    panel?.querySelector<HTMLAnchorElement>("a")?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const items = [toggle, ...Array.from(panel.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"))].filter(
        (node): node is HTMLElement => Boolean(node),
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    const desktop = window.matchMedia("(min-width: 981px)");
    function closeOnDesktop() {
      if (desktop.matches) setOpen(false);
    }

    window.addEventListener("keydown", onKey);
    desktop.addEventListener("change", closeOnDesktop);
    return () => {
      window.removeEventListener("keydown", onKey);
      desktop.removeEventListener("change", closeOnDesktop);
    };
  }, [open]);

  const wasOpen = useRef(false);
  useEffect(() => {
    if (wasOpen.current && !open) toggleRef.current?.focus();
    wasOpen.current = open;
  }, [open]);

  const accountHref = current === "portal" ? "/portal" : "/signin";
  const accountLabel = current === "portal" ? "Portal" : "Sign In";

  return (
    <header className={`site-header site-header-${surface}`}>
      <div className="site-header-bar">
        <Logo surface={surface} />
        <button
          ref={toggleRef}
          className="nav-toggle"
          type="button"
          aria-expanded={open}
          aria-controls={menuId}
          onClick={() => setOpen((value) => !value)}
        >
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          <span className={`nav-toggle-icon ${open ? "is-open" : ""}`} aria-hidden="true" />
        </button>
        <div id={menuId} ref={panelRef} className={`nav-panel ${open ? "is-open" : ""}`}>
          <nav aria-label="Primary">
            <ul>
              {links.map((link) => (
                <li key={link.id}>
                  <a href={link.href} aria-current={current === link.id ? "page" : undefined} onClick={() => setOpen(false)}>
                    {link.label}
                  </a>
                </li>
              ))}
              <li>
                <a href={accountHref} aria-current={current === "signin" ? "page" : undefined} onClick={() => setOpen(false)}>
                  {accountLabel}
                </a>
              </li>
              <li>
                <a className={`btn ${surface === "dark" ? "btn-cream" : "btn-accent"}`} href="/#products" onClick={() => setOpen(false)}>
                  Explore Our Products
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter({ accountHref = "/signin", accountLabel = "Sign In" }: { accountHref?: string; accountLabel?: string }) {
  return (
    <footer className="site-footer">
      <div className="footer-main">
        <div className="footer-brand">
          <Logo surface="dark" />
          <p>Thoughtful technology, rooted in people.</p>
        </div>
        <div className="footer-links">
          <div>
            <p>Products</p>
            <ul>
              {products.map((product) => (
                <li key={product.slug}><a href={product.href}>{product.name}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <p>Company</p>
            <ul>
              <li><a href="/#about">About</a></li>
              <li><a href="/#building">Development</a></li>
              <li><a href="/support">Contact</a></li>
            </ul>
          </div>
          <div>
            <p>Support</p>
            <ul>
              <li><a href="/support">Support</a></li>
              <li><a href="/support#documentation">Documentation when available</a></li>
            </ul>
          </div>
          <div>
            <p>Account</p>
            <ul>
              <li><a href={accountHref}>{accountLabel}</a></li>
            </ul>
          </div>
          <div>
            <p>Legal</p>
            <ul>
              <li><a href="/privacy">Privacy</a></li>
              <li><a href="/terms">Terms</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div className="footer-base">
        <p>© 2026 Blue Ash Digital</p>
        <p>Ownership · Privacy · Usefulness</p>
      </div>
    </footer>
  );
}

export function usePageMeta(title: string, description: string, path: string) {
  useEffect(() => {
    document.title = title;
    setMeta("name", "description", description);
    setMeta("property", "og:title", title);
    setMeta("property", "og:description", description);
    setMeta("property", "og:url", `https://blueashdigital.tech${path}`);
  }, [title, description, path]);
}

function setMeta(attribute: "name" | "property", key: string, value: string) {
  const node = document.head.querySelector(`meta[${attribute}="${key}"]`);
  if (node) node.setAttribute("content", value);
}

export function SiteFrame({
  surface,
  current,
  children,
}: {
  surface: Surface;
  current: string;
  children: ReactNode;
}) {
  useEffect(() => {
    document.body.classList.add("site-body");
    return () => document.body.classList.remove("site-body");
  }, []);

  return (
    <div className="site">
      <a className="skip" href="#content">Skip to content</a>
      <SiteHeader surface={surface} current={current} />
      <main id="content">{children}</main>
      <SiteFooter
        accountHref={current === "portal" ? "/portal" : "/signin"}
        accountLabel={current === "portal" ? "Portal" : "Sign In"}
      />
    </div>
  );
}
