expected_selectors = ["title_selector", "content_selector", "link_selector"]

articles = ['referrers', 'title_selector', "link_selector"]

print(list(selector in articles for selector in expected_selectors))
print(all(selector in articles for selector in expected_selectors))
for selector in articles:
    expected_selectors.remove(selector) if selector in expected_selectors else None
print(expected_selectors)

print(any(expected_selectors))
with articles[0] as article:
    print(article)