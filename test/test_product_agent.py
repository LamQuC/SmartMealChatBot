from src.agents.product_search_agent import ProductSearchAgent

def test_product_search():

    agent = ProductSearchAgent()

    result = agent.run("socola ferrero")

    assert "results" in result
    assert len(result["results"]) > 0