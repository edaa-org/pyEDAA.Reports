library ieee;
use     ieee.numeric_std.all;


package Functions is
	function log2ceil(value : natural) return natural;
	function max(left : integer; right : integer) return integer;
end package;


package body Functions is
	function log2ceil(value : natural) return natural is
		variable result : natural := 0;
	begin
		while 2 ** result < value loop
			result := result + 1;
		end loop;
		return result;
	end function;

	function max(left : integer; right : integer) return integer is
	begin
		if left > right then
			return left;
		end if;
		return right;
	end function;
end package body;
