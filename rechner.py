import ast
import operator
import streamlit as st


st.set_page_config(
    page_title="Visueller Taschenrechner",
    page_icon="🧮",
    layout="centered",
)


# Erlaubte Rechenoperationen
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def sichere_berechnung(expression: str) -> float:
    """
    Berechnet einen mathematischen Ausdruck sicher.
    Es werden ausschließlich Zahlen und erlaubte Operatoren akzeptiert.
    """
    tree = ast.parse(expression, mode="eval")

    def berechne(node):
        if isinstance(node, ast.Expression):
            return berechne(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Ungültiger Wert")

        if isinstance(node, ast.BinOp):
            linker_wert = berechne(node.left)
            rechter_wert = berechne(node.right)

            operator_funktion = OPERATORS.get(type(node.op))
            if operator_funktion is None:
                raise ValueError("Operator nicht erlaubt")

            return operator_funktion(linker_wert, rechter_wert)

        if isinstance(node, ast.UnaryOp):
            operator_funktion = OPERATORS.get(type(node.op))
            if operator_funktion is None:
                raise ValueError("Operator nicht erlaubt")

            return operator_funktion(berechne(node.operand))

        raise ValueError("Ungültiger Ausdruck")

    return berechne(tree)


def format_ergebnis(wert):
    """Formatiert das Ergebnis ohne unnötige Nachkommastellen."""
    if isinstance(wert, float) and wert.is_integer():
        return str(int(wert))

    return f"{wert:.10g}"


# Initialisierung des Session-Status
if "ausdruck" not in st.session_state:
    st.session_state.ausdruck = ""

if "ergebnis" not in st.session_state:
    st.session_state.ergebnis = ""


# Benutzerdefiniertes Styling
st.markdown(
    """
    <style>
        .main {
            max-width: 500px;
            margin: auto;
        }

        div.stButton > button {
            width: 100%;
            height: 58px;
            font-size: 24px;
            border-radius: 12px;
        }

        .display {
            background-color: #1e1e1e;
            color: white;
            padding: 20px;
            border-radius: 14px;
            text-align: right;
            margin-bottom: 18px;
            min-height: 95px;
        }

        .expression {
            color: #bdbdbd;
            font-size: 20px;
            min-height: 28px;
        }

        .result {
            font-size: 36px;
            font-weight: bold;
            margin-top: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("🧮 Taschenrechner")

# Anzeige
anzeige_ergebnis = (
    st.session_state.ergebnis
    if st.session_state.ergebnis
    else "0"
)

st.markdown(
    f"""
    <div class="display">
        <div class="expression">{st.session_state.ausdruck or " "}</div>
        <div class="result">{anzeige_ergebnis}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def taste_verarbeiten(taste: str):
    if taste == "C":
        st.session_state.ausdruck = ""
        st.session_state.ergebnis = ""

    elif taste == "⌫":
        st.session_state.ausdruck = st.session_state.ausdruck[:-1]
        st.session_state.ergebnis = ""

    elif taste == "=":
        if not st.session_state.ausdruck:
            return

        try:
            wert = sichere_berechnung(st.session_state.ausdruck)
            st.session_state.ergebnis = format_ergebnis(wert)
        except ZeroDivisionError:
            st.session_state.ergebnis = "Division durch 0"
        except (SyntaxError, ValueError):
            st.session_state.ergebnis = "Ungültiger Ausdruck"

    elif taste == ".":
        # Verhindert mehrere Dezimalpunkte in derselben Zahl
        aktueller_teil = st.session_state.ausdruck.split(
            "+", "-", "*", "/"
        )[-1]

        if "." not in aktueller_teil:
            st.session_state.ausdruck += taste
            st.session_state.ergebnis = ""

    else:
        st.session_state.ausdruck += taste
        st.session_state.ergebnis = ""


# Taschenrechner-Tasten
tasten = [
    ["C", "⌫", "(", ")"],
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "=", "+"],
]

for zeile in tasten:
    spalten = st.columns(4)

    for index, taste in enumerate(zeile):
        with spalten[index]:
            if st.button(taste, key=f"taste_{taste}_{index}_{len(zeile)}"):
                taste_verarbeiten(taste)
                st.rerun()
