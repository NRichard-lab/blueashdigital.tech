export type ProductStatus = "In Development";

export type CatalogProduct = {
  slug: string;
  name: string;
  descriptor: string;
  status: ProductStatus;
  href: string;
  summary: string;
  detail: string;
  linkLabel: string;
};

export const products: CatalogProduct[] = [
  {
    slug: "blue-ash-reel",
    name: "Blue Ash Reel",
    descriptor: "Reel",
    status: "In Development",
    href: "/products/blue-ash-reel",
    summary: "A personal media platform designed to organize, watch, and share your own media while keeping your library at home.",
    detail: "Your personal media, beautifully organized and ready to share, all in one place. Your library stays at home, with built-in privacy and only essential data collected.",
    linkLabel: "Learn About Blue Ash Reel",
  },
];
