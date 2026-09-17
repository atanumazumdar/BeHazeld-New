export const GST_RATE = 0.05;
export const OPERATING_COST_RATE = 0.05;
export const GST_EFFECTIVE_DATE = '2026-09-01';

export function gstRateForDate(date: string | Date = new Date()): number {
  const value = typeof date === 'string' ? date.slice(0, 10) : date.toISOString().slice(0, 10);
  return value >= GST_EFFECTIVE_DATE ? GST_RATE : 0;
}

export function addGst(value: number, date: string | Date = new Date()): number {
  return value * (1 + gstRateForDate(date));
}

export function skuNetProfit(baseCost: number, baseSellingPrice: number): number {
  const costIncludingGst = addGst(baseCost);
  const operatingCost = baseSellingPrice * OPERATING_COST_RATE;
  return baseSellingPrice - costIncludingGst - operatingCost;
}

export function skuNetMargin(baseCost: number, baseSellingPrice: number): number {
  const finalSellingPrice = addGst(baseSellingPrice);
  if (finalSellingPrice <= 0) return 0;
  return (skuNetProfit(baseCost, baseSellingPrice) / finalSellingPrice) * 100;
}
