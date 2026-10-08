package Utilities is
	function Maximum(left : integer; right : integer) return integer;
end package;


package body Utilities is
	function Maximum(left : integer; right : integer) return integer is
	begin
		if left > right then
			return left;
		end if;
		return right;
	end function;
end package body;
