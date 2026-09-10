#include <QApplication>
#include <QWidget>
#include <QLineEdit>
#include <QLabel>
#include <QVBoxLayout>
#include <QString>
#include <QChar>

// Reverses by Unicode code point (handles UTF-16 surrogate pairs, e.g. emoji).
static QString reverseQString(const QString& s) {
    QString out;
    out.reserve(s.size());
    int i = s.size() - 1;
    while (i >= 0) {
        QChar c = s.at(i);
        if (c.isLowSurrogate() && i - 1 >= 0 &&
            s.at(i - 1).isHighSurrogate()) {
            out.append(s.at(i - 1)); // high surrogate
            out.append(c);           // low surrogate
            i -= 2;
        } else {
            out.append(c);
            i -= 1;
        }
    }
    return out;
}

class Reverser : public QWidget {
public:
    Reverser() {
        auto* layout = new QVBoxLayout(this);

        layout->addWidget(new QLabel("Input:", this));
        input_ = new QLineEdit(this);
        input_->setPlaceholderText("Type or paste text here…");
        layout->addWidget(input_);

        layout->addWidget(new QLabel("Reversed:", this));
        result_ = new QLabel(this);
        result_->setWordWrap(true);
        result_->setFrameShape(QFrame::StyledPanel);
        layout->addWidget(result_);

        connect(input_, &QLineEdit::textChanged, this,
                [this](const QString& t) {
                    result_->setText(reverseQString(t));
                });

        setWindowTitle("String Reverser");
        resize(440, 220);
    }

private:
    QLineEdit* input_;
    QLabel* result_;
};

int main(int argc, char** argv) {
    QApplication app(argc, argv);
    Reverser w;
    w.show();
    return app.exec();
}