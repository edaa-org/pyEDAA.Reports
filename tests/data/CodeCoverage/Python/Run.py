"""Exercise the fixture package partly, so the report has covered, missed, partial and excluded lines."""
from myPackage.Shapes       import Circle, Rectangle
from myPackage.Units.Length import ToMeters

Circle(1.0).Area()
Rectangle(2.0, 3.0).Area()
Rectangle(2.0, 3.0).IsSquare()
ToMeters(1.0, "m")
ToMeters(5.0, "cm")
