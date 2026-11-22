fn main() {
    let r: float;
    r = media(1.5, 2.5);
    mostra(r, 'a');
    mostra(r, 'b');
    println("{}", media(r, r));
}

fn media(a: float, b: float) -> float {
    return (a + b) / 2.0;
}

fn mostra(v: float, c: char) {
    println("{} {}", v, c);
}
