export interface ChartDomain {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

export function chartDomain(
  points: { rvol: number; displacement: number }[],
): ChartDomain {
  let dataXMax = 0
  let dataYMax = 0
  let xMin = 0
  let yMin = 0
  for (const point of points) {
    dataXMax = Math.max(dataXMax, point.rvol)
    dataYMax = Math.max(dataYMax, point.displacement)
    xMin = Math.min(xMin, point.rvol)
    yMin = Math.min(yMin, point.displacement)
  }
  const xCeiling = Math.max(4, dataXMax)
  const yCeiling = Math.max(2, dataYMax)
  return {
    xMin,
    xMax: dataXMax >= 4 ? Number((xCeiling * 1.05).toFixed(4)) : xCeiling,
    yMin,
    yMax: dataYMax >= 2 ? Number((yCeiling * 1.05).toFixed(4)) : yCeiling,
  }
}
