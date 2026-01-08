from yahoo_fin import stock_info as si
from yahoo_fin.stock_info import get_data
def main():
    # Get live price
    price = si.get_live_price("AAPL")
    print(f"Apple Live Price: {price}")

    # Get quote table with fundamentals
    quote_table = si.get_quote_table("AAPL", dict_result=False)
    print(quote_table)

    # Get historical data
    historical = get_data("AAPL", start_date="01/01/2022", end_date="01/10/2022", interval="1d")
    print(historical)


if __name__ == "__main__":
    main()
