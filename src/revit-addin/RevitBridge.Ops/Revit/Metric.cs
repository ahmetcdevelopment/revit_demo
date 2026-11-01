using Autodesk.Revit.DB;

namespace RevitBridge.Revit;

/// <summary>Specs are in metres; Revit stores feet internally.</summary>
public static class Metric
{
    public static double FromMetres(double m) => UnitUtils.ConvertToInternalUnits(m, UnitTypeId.Meters);

    public static double ToMetres(double feet) => UnitUtils.ConvertFromInternalUnits(feet, UnitTypeId.Meters);

    public static XYZ Xyz(double xMetres, double yMetres, double zMetres = 0.0) =>
        new(FromMetres(xMetres), FromMetres(yMetres), FromMetres(zMetres));
}
