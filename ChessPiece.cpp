#include "ChessPiece.h"
#include "ChessBoard.h"
#include <qmath.h>

ChessPiece::ChessPiece(const QString& type, const QPixmap& pixmap, ChessBoard* board, QGraphicsItem *parent)
    : QGraphicsEllipseItem(2, 2, 12, 12, parent), pieceType(type), m_board(board) {
    
    // Hitbox Ayarları
    setPen(Qt::NoPen); 
    setBrush(Qt::NoBrush); 
    setFlag(QGraphicsItem::ItemIsMovable);

    // Sprite Ayarları
    m_sprite = new QGraphicsPixmapItem(pixmap, this);
    m_sprite->setAcceptedMouseButtons(Qt::NoButton); // Tıklamalar Hitbox'a geçsin

    // Resmi Hitbox içine yerleştir
    int xOffset = (16 - pixmap.width()) / 2;
    int yOffset = squareSize - pixmap.height();
    m_sprite->setPos(xOffset, yOffset);
}

void ChessPiece::mousePressEvent(QGraphicsSceneMouseEvent *event) {
    originalPos = pos();
    originCol = static_cast<int>(originalPos.x()) / squareSize;
    originRow = static_cast<int>(originalPos.y()) / squareSize;
    
    setZValue(100); // YENİ: Taşı tuttuğunda havaya kaldır
    
    QGraphicsEllipseItem::mousePressEvent(event);
}

void ChessPiece::mouseReleaseEvent(QGraphicsSceneMouseEvent *event) {
    QGraphicsEllipseItem::mouseReleaseEvent(event); // Bırakma işlemini Qt'ye bildir
    setZValue(1); // Taşı yere bırak

    // MANYETİZMA (Kusursuz UX)
    qreal currentX = scenePos().x();
    qreal currentY = scenePos().y();

    int targetCol = qRound(currentX / static_cast<qreal>(squareSize));
    int targetRow = qRound(currentY / static_cast<qreal>(squareSize));

    // Sınırları Koru (Tahtadan dışarı fırlatmayı engelle)
    targetCol = qBound(0, targetCol, 7);
    targetRow = qBound(0, targetRow, 7);

    // Taşı mıknatıs gibi hedefe yapıştır (Snap)
    setPos(targetCol * squareSize, targetRow * squareSize);

    // Eğer taş hiç hareket etmediyse işlemi iptal et
    if (originCol == targetCol && originRow == targetRow) return;

    // Koordinatları satranç diline çevir (Örn: e7e8)
    QString uciMove = toChessNotation(originCol, originRow) + toChessNotation(targetCol, targetRow);
    
    // --- YENİ: OTOMATİK VEZİR TERFİSİ (Promotion) ---
    // Beyaz piyon (P) 0. satıra veya Siyah piyon (p) 7. satıra ulaşırsa 'q' ekle
    if ((pieceType == "P" && targetRow == 0) || (pieceType == "p" && targetRow == 7)) {
        uciMove += "q";
        qDebug() << "SİSTEM: Piyon terfisi tespit edildi! Yeni hamle komutu:" << uciMove;
    }
    // -------------------------------------------------

    qDebug() << "SİSTEM: Manyetizma Çalıştı -> Gönderilen Hamle:" << uciMove;

    m_board->attemptMove(this, uciMove);
}

void ChessPiece::snapBack() {
    setPos(originalPos);
}

QString ChessPiece::toChessNotation(int col, int row) {
    return QString("%1%2").arg(char('a' + col)).arg(8 - row);
}

// --- YENİ X-RAY DEBUG FONKSİYONU UYGULAMASI ---
void ChessPiece::setDebugView(bool enable) {
    if (enable) {
        // X-Ray Modu: Resmi şeffaflaştır, Hitbox çerçevesini göster
        setPen(QPen(Qt::blue, 1)); // Mavi çerçeveyi aç (0,0'dan 16,16'ya)
        m_sprite->setOpacity(0.3);   // Resmi %30 şeffaf yap (arkasını görelim)
    } else {
        // Normal Mod: Röntgeni kapat, resmi full göster
        setPen(Qt::NoPen);          // Çerçeveyi gizle
        m_sprite->setOpacity(1.0);   // Resmi full opak yap
    }
}