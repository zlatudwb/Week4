def main():
    while True:
        user_input = input("힘(kN)을 입력하세요 (종료: q): ").strip()

        if user_input.lower() == "q":
            print("프로그램을 종료합니다.")
            break

        try:
            kilonewtons = float(user_input)
        except ValueError:
            print("오류: 숫자 또는 q를 입력하세요.")
            continue

        newtons = kilonewtons * 1000
        kilogram_force = newtons / 9.81
        print(f"{newtons:.2f} N, 약 {kilogram_force:.2f} kgf")


if __name__ == "__main__":
    main()
