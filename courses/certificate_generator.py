from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
import qrcode
from io import BytesIO


class CertificateGenerator:
    def __init__(self, certificate):
        self.certificate = certificate
        self.width, self.height = landscape(A4)

    def generate(self):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        self._draw_background(c)
        self._draw_border(c)
        self._draw_header(c)
        self._draw_content(c)
        self._draw_qr_code(c)
        self._draw_footer(c)

        c.save()
        buffer.seek(0)
        return buffer

    def _draw_background(self, c):
        c.setFillColor(HexColor('#f8fafc'))
        c.rect(0, 0, self.width, self.height, fill=True, stroke=False)

        c.setFillColor(HexColor('#4f46e5'))
        c.circle(0, self.height, 80, fill=True, stroke=False)
        c.setFillColor(HexColor('#6366f1'))
        c.circle(0, self.height, 50, fill=True, stroke=False)

        c.setFillColor(HexColor('#4f46e5'))
        c.circle(self.width, 0, 80, fill=True, stroke=False)
        c.setFillColor(HexColor('#6366f1'))
        c.circle(self.width, 0, 50, fill=True, stroke=False)

        c.setFillColor(HexColor('#4f46e5'))
        c.circle(self.width, self.height, 60, fill=True, stroke=False)
        c.circle(0, 0, 60, fill=True, stroke=False)

    def _draw_border(self, c):
        c.setStrokeColor(HexColor('#4f46e5'))
        c.setLineWidth(3)
        c.roundRect(30, 30, self.width - 60, self.height - 60, 20, stroke=True, fill=False)

        c.setStrokeColor(HexColor('#6366f1'))
        c.setLineWidth(1)
        c.roundRect(40, 40, self.width - 80, self.height - 80, 15, stroke=True, fill=False)

    def _draw_header(self, c):
        center_x = self.width / 2

        c.setFillColor(HexColor('#4f46e5'))
        c.circle(center_x, self.height - 100, 30, fill=True, stroke=False)

        c.setFillColor(HexColor('#1e293b'))
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(center_x, self.height - 150, "SERTIFIKAT")

        c.setFillColor(HexColor('#64748b'))
        c.setFont("Helvetica", 14)
        c.drawCentredString(center_x, self.height - 175, "CERTIFICATE OF COMPLETION")

    def _draw_content(self, c):
        center_x = self.width / 2

        c.setFillColor(HexColor('#64748b'))
        c.setFont("Helvetica", 14)
        c.drawCentredString(center_x, self.height - 220, "Ushbu sertifikat tasdiqlaydiki,")

        c.setFillColor(HexColor('#1e293b'))
        c.setFont("Helvetica-Bold", 32)
        student_name = self.certificate.student.get_full_name()
        c.drawCentredString(center_x, self.height - 260, student_name)

        c.setStrokeColor(HexColor('#4f46e5'))
        c.setLineWidth(2)
        name_width = c.stringWidth(student_name, "Helvetica-Bold", 32)
        c.line(center_x - name_width / 2 - 20, self.height - 275,
               center_x + name_width / 2 + 20, self.height - 275)

        c.setFillColor(HexColor('#64748b'))
        c.setFont("Helvetica", 14)
        c.drawCentredString(center_x, self.height - 305, "quyidagi kursni muvaffaqiyatli yakunladi:")

        c.setFillColor(HexColor('#4f46e5'))
        c.setFont("Helvetica-Bold", 24)
        course_title = self.certificate.course.title
        if len(course_title) > 50:
            course_title = course_title[:47] + "..."
        c.drawCentredString(center_x, self.height - 340, course_title)

        c.setFillColor(HexColor('#f1f5f9'))
        c.roundRect(center_x - 200, self.height - 400, 400, 45, 10, fill=True, stroke=False)

        c.setFillColor(HexColor('#475569'))
        c.setFont("Helvetica", 11)
        course_info = f"O'qituvchi: {self.certificate.course.teacher.get_full_name()}"
        c.drawCentredString(center_x, self.height - 380, course_info)

        lessons_count = self.certificate.course.total_lessons
        c.drawCentredString(center_x, self.height - 395, f"Darslar soni: {lessons_count} ta")

    def _draw_qr_code(self, c):
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        verify_url = f"http://127.0.0.1:8000/certificates/verify/{self.certificate.id}/"
        qr.add_data(verify_url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="#4f46e5", back_color="white")

        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        qr_image = ImageReader(qr_buffer)
        c.drawImage(qr_image, self.width - 150, 60, width=80, height=80)

        c.setFillColor(HexColor('#64748b'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.width - 110, 50, "Tekshirish uchun skanerlang")

    def _draw_footer(self, c):
        center_x = self.width / 2

        c.setFillColor(HexColor('#64748b'))
        c.setFont("Helvetica", 11)

        issued_date = self.certificate.issued_at.strftime("%d.%m.%Y")
        c.drawString(60, 100, f"Berilgan sana: {issued_date}")
        c.drawString(60, 85, f"Sertifikat raqami: {self.certificate.certificate_number}")

        c.setStrokeColor(HexColor('#cbd5e1'))
        c.setLineWidth(1)
        c.line(center_x - 100, 90, center_x + 100, 90)

        c.setFillColor(HexColor('#475569'))
        c.setFont("Helvetica", 10)
        c.drawCentredString(center_x, 75, "Platforma ma'muriyati")

        c.setFillColor(HexColor('#4f46e5'))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(center_x, 55, "LMS Platform")

        c.setFillColor(HexColor('#94a3b8'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(center_x, 40,
                            f"Sertifikatni tekshirish: http://127.0.0.1:8000/certificates/verify/{self.certificate.id}/")