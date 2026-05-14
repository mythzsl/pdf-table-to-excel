import { SITE } from "../site";

const paths = [
  "/pdf-table-to-excel/",
  "/pdf-to-excel/",
  "/extract-tables-from-pdf/",
  "/pdf-to-csv/",
  "/privacy/",
  "/terms/",
  "/guides/how-to-extract-tables-from-a-pdf-to-excel/",
  "/guides/pdf-to-excel-vs-pdf-table-extraction/",
  "/guides/why-pdf-to-excel-conversions-break-table-formatting/",
  "/guides/how-to-convert-bank-statement-pdf-tables-to-excel/",
  "/guides/best-free-pdf-table-extractors/"
];

export function GET() {
  const urls = paths
    .map((path) => `  <url><loc>${new URL(path, SITE.url).toString()}</loc></url>`)
    .join("\n");

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>`, {
    headers: {
      "Content-Type": "application/xml"
    }
  });
}
