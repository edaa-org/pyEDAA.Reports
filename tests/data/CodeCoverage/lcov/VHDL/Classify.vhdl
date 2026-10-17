package Classify is
	function Sign(value : integer) return integer;
	function InRange(value : integer; low : integer; high : integer) return boolean;
	function Twice(value : integer) return integer;
end package;


package body Classify is
	function Sign(value : integer) return integer is
	begin
		if value < 0 then
			return -1;
		elsif value > 0 then
			return 1;
		end if;
		return 0;
	end function;

	function InRange(value : integer; low : integer; high : integer) return boolean is
	begin
		return value >= low and value <= high;
	end function;

	function Twice(value : integer) return integer is
	begin
		if value < 0 then
			return 0;
		end if;
		return 2 * value;
	end function;
end package body;
