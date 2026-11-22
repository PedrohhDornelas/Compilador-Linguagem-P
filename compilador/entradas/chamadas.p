fn dobro(x: int) -> int {
    return x * 2;
}

fn soma3(a: int, b: int, c: int) -> int {
    return a + b + c;
}

fn main() {
    let r, s: int;
    r = dobro(4);
    s = soma3(r, dobro(1), 3);
    dobro(7);
    soma3(1, 2, 3);
    println("{} {}", r, s);
}
