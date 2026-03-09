# Technical Design: Bitcoin Technical Indicators

Adding interactive technical indicators (MACD, SMAs, EMAs) to the Bitcoin analysis dashboard with multi-currency support (USD, CHF, EUR).

## Architecture

The indicators are already available in the Databricks table `prod.dlh_silver__crypto_prices.obt_fact_day_btc`. The frontend will be updated to fetch these additional columns and render them using `chart.js`.

### Data Flow
1. **Fetching**: Update `bitcoin-data-server.ts` (if needed) to ensure the additional columns are fetched from Databricks.
2. **State Management**: `DashboardClient.tsx` will maintain a set of active indicators.
3. **Rendering**: `PriceChart.tsx` will receive the active indicators and add corresponding datasets to the chart.

## UI Components

### 1. Multi-Select Indicator Dropdown
- **Position**: Next to the price/forecast toggle in the header.
- **Options**:
    - **RSI**: Moves from a separate toggle into this dropdown.
    - **MACD**: Shows MACD line, Signal line, and Histogram in a separate sub-chart.
    - **3 SMA**: 7-day, 50-day, and 200-day Simple Moving Averages overlayed.
    - **3 EMA**: 7-day, 50-day, and 200-day Exponential Moving Averages overlayed.

### 2. Chart Updates (`PriceChart.tsx`)
- **Overlay Indicators (SMA/EMA)**: Rendered as thin lines on the main price Y-axis.
- **Sub-chart Indicators (RSI, MACD)**: Rendered in dedicated Y-axes stacked at the bottom of the chart area.
    - RSI: Existing functionality.
    - MACD: New stack weight. MACD Histogram will use a "bar" type if possible or custom plugin rendering.

## Testing Strategy

### Unit Tests
- Test indicator data parsing in `lib` utilities.
- Test `PriceChart.tsx` props handling.

### Browser Testing
- Verify dropdown interaction.
- Verify chart rendering for each indicator type in both Line and Candlestick modes.
- Verify currency switching correctly updates indicator values.

## Implementation Phases
1. **Setup**: Create branch and initial test files.
2. **Data Layer**: Update Zod schemas and fetching logic.
3. **UI Component**: Add `IndicatorSelector` component.
4. **Chart Integration**: Update `PriceChart` for overlay and sub-chart rendering.
5. **QA & Submission**: Local tests, PR creation.
