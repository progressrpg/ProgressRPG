import { useEffect } from 'react';

function upsertMeta(selector, attributes) {
  let element = document.head.querySelector(selector);

  if (!element) {
    element = document.createElement('meta');
    document.head.appendChild(element);
  }

  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });

  return element;
}

function upsertLink(selector, attributes) {
  let element = document.head.querySelector(selector);

  if (!element) {
    element = document.createElement('link');
    document.head.appendChild(element);
  }

  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });

  return element;
}

function upsertJsonLd(id, data) {
  let element = document.head.querySelector(`#${id}`);

  if (!element) {
    element = document.createElement('script');
    element.type = 'application/ld+json';
    element.id = id;
    document.head.appendChild(element);
  }

  element.textContent = JSON.stringify(data);
  return element;
}

export default function Seo({
  title,
  description,
  canonical,
  robots,
  ogType = 'website',
  structuredData,
}) {
  useEffect(() => {
    const previousTitle = document.title;
    const descriptionMeta = document.head.querySelector('meta[name="description"]');
    const robotsMeta = document.head.querySelector('meta[name="robots"]');
    const ogTitleMeta = document.head.querySelector('meta[property="og:title"]');
    const ogDescriptionMeta = document.head.querySelector('meta[property="og:description"]');
    const ogTypeMeta = document.head.querySelector('meta[property="og:type"]');
    const ogUrlMeta = document.head.querySelector('meta[property="og:url"]');
    const twitterCardMeta = document.head.querySelector('meta[name="twitter:card"]');
    const twitterTitleMeta = document.head.querySelector('meta[name="twitter:title"]');
    const twitterDescriptionMeta = document.head.querySelector('meta[name="twitter:description"]');
    const canonicalLink = document.head.querySelector('link[rel="canonical"]');
    const jsonLdScript = document.head.querySelector('#home-page-structured-data');

    const previousDescription = descriptionMeta?.getAttribute('content') ?? null;
    const previousRobots = robotsMeta?.getAttribute('content') ?? null;
    const previousOgTitle = ogTitleMeta?.getAttribute('content') ?? null;
    const previousOgDescription = ogDescriptionMeta?.getAttribute('content') ?? null;
    const previousOgType = ogTypeMeta?.getAttribute('content') ?? null;
    const previousOgUrl = ogUrlMeta?.getAttribute('content') ?? null;
    const previousTwitterCard = twitterCardMeta?.getAttribute('content') ?? null;
    const previousTwitterTitle = twitterTitleMeta?.getAttribute('content') ?? null;
    const previousTwitterDescription = twitterDescriptionMeta?.getAttribute('content') ?? null;
    const previousCanonical = canonicalLink?.getAttribute('href') ?? null;
    const previousStructuredData = jsonLdScript?.textContent ?? null;

    const currentDescriptionMeta = upsertMeta('meta[name="description"]', { name: 'description', content: description });
    const currentRobotsMeta = upsertMeta('meta[name="robots"]', { name: 'robots', content: robots });
    const currentOgTitleMeta = upsertMeta('meta[property="og:title"]', { property: 'og:title', content: title });
    const currentOgDescriptionMeta = upsertMeta('meta[property="og:description"]', { property: 'og:description', content: description });
    const currentOgTypeMeta = upsertMeta('meta[property="og:type"]', { property: 'og:type', content: ogType });
    const currentOgUrlMeta = upsertMeta('meta[property="og:url"]', { property: 'og:url', content: canonical });
    const currentTwitterCardMeta = upsertMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary' });
    const currentTwitterTitleMeta = upsertMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: title });
    const currentTwitterDescriptionMeta = upsertMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: description });
    const currentCanonicalLink = upsertLink('link[rel="canonical"]', { rel: 'canonical', href: canonical });
    let currentJsonLdScript = null;

    if (structuredData) {
      currentJsonLdScript = upsertJsonLd('home-page-structured-data', structuredData);
    }

    document.title = title;

    return () => {
      document.title = previousTitle;
      if (descriptionMeta) {
        currentDescriptionMeta.setAttribute('content', previousDescription ?? '');
      } else {
        currentDescriptionMeta.remove();
      }
      if (robotsMeta) {
        currentRobotsMeta.setAttribute('content', previousRobots ?? '');
      } else {
        currentRobotsMeta.remove();
      }
      if (ogTitleMeta) {
        currentOgTitleMeta.setAttribute('content', previousOgTitle ?? '');
      } else {
        currentOgTitleMeta.remove();
      }
      if (ogDescriptionMeta) {
        currentOgDescriptionMeta.setAttribute('content', previousOgDescription ?? '');
      } else {
        currentOgDescriptionMeta.remove();
      }
      if (ogTypeMeta) {
        currentOgTypeMeta.setAttribute('content', previousOgType ?? '');
      } else {
        currentOgTypeMeta.remove();
      }
      if (ogUrlMeta) {
        currentOgUrlMeta.setAttribute('content', previousOgUrl ?? '');
      } else {
        currentOgUrlMeta.remove();
      }
      if (twitterCardMeta) {
        currentTwitterCardMeta.setAttribute('content', previousTwitterCard ?? '');
      } else {
        currentTwitterCardMeta.remove();
      }
      if (twitterTitleMeta) {
        currentTwitterTitleMeta.setAttribute('content', previousTwitterTitle ?? '');
      } else {
        currentTwitterTitleMeta.remove();
      }
      if (twitterDescriptionMeta) {
        currentTwitterDescriptionMeta.setAttribute('content', previousTwitterDescription ?? '');
      } else {
        currentTwitterDescriptionMeta.remove();
      }
      if (canonicalLink) {
        currentCanonicalLink.setAttribute('href', previousCanonical ?? '');
      } else {
        currentCanonicalLink.remove();
      }

      if (currentJsonLdScript) {
        if (previousStructuredData) {
          currentJsonLdScript.textContent = previousStructuredData;
        } else {
          currentJsonLdScript.remove();
        }
      }
    };
  }, [canonical, description, ogType, robots, structuredData, title]);

  return null;
}
