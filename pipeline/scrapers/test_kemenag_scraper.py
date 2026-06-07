# pipeline/scrapers/test_kemenag_scraper.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kemenag_scraper import parse_agents

SAMPLE_HTML = """
<table class="views-table">
  <tbody>
    <tr>
      <td>PPIU-001</td><td>PT Umroh Barokah</td>
      <td>Jakarta Selatan</td><td>DKI Jakarta</td>
      <td>31-12-2026</td>
    </tr>
  </tbody>
</table>
"""

def test_parse_agents():
    agents = parse_agents(SAMPLE_HTML)
    assert len(agents) == 1
    assert agents[0]["license_number"] == "PPIU-001"
    assert agents[0]["name"] == "PT Umroh Barokah"
    assert agents[0]["ppiu_verified"] is True
