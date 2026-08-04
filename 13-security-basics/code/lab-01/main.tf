resource "aws_security_group" "bad" {
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # Open to the world!
  }
}

resource "aws_s3_bucket" "bad" {
  bucket = "my-public-bucket"
  acl    = "public-read" # Public bucket!
}
